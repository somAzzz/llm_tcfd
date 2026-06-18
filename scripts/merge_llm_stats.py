#!/usr/bin/env python3
"""Merge LLM-validated cooccurrence statistics into frequency CSVs.

This script:
1. Loads tcfd_validated.json and builds a keyword -> dimension mapping (first match wins)
2. Processes all year directories in output/evaluate_cooccurrence/ in parallel
3. For each year, reads results.jsonl, filters is_tcfd_related==True, maps keyword_a to dimension
4. Aggregates counts by (filename, dimension)
5. Merges results into existing CSVs at output/frequency/词频统计_{政策,市场,技术}.csv
   adding columns llm_sum_class_AB and llm_sum_class_AB_每万字

Usage:
    python scripts/merge_llm_stats.py
"""

import argparse
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd


def load_keyword_dimension_mapping(tcfd_validated_path: Path) -> dict[str, str]:
    """Load tcfd_validated.json and build keyword -> dimension mapping.

    The tcfd_validated.json has structure:
        {"技术": {"keyword1": [...], ...}, "市场": {...}, "政策": {...}}

    Uses first match if a keyword appears in multiple dimensions.
    Iterates dimensions in order: 政策, 市场, 技术 (first match wins).
    """
    keyword_dim_map = {}

    with open(tcfd_validated_path, encoding="utf-8") as f:
        data = json.load(f)

    # Iterate dimensions in order - first match wins
    for dim in ["政策", "市场", "技术"]:
        if dim in data:
            for category_keywords in data[
                dim
            ].values():  # Iterate over inner dict values
                for keyword in category_keywords:
                    if keyword not in keyword_dim_map:
                        keyword_dim_map[keyword] = dim

    return keyword_dim_map


def process_year_directory(
    args: tuple[Path, dict[str, str]],
) -> tuple[dict[tuple[str, str], int], dict[str, int], dict[str, int]]:
    """Process a single year directory and return counts by (filename_stripped, dimension).

    Args:
        args: Tuple of (year_dir, keyword_dim_map)

    Returns:
        Tuple of:
        - Dict mapping (filename_without_md, dimension) -> count
        - Dict mapping unmapped keyword_a -> count
        - Dict with per-year stats: total_records, tcfd_related, mapped, unmapped
    """
    year_dir, keyword_dim_map = args
    results_path = year_dir / "results.jsonl"

    if not results_path.exists():
        return {}, {}, {"total_records": 0, "tcfd_related": 0, "mapped": 0, "unmapped": 0}

    counts = defaultdict(int)
    unmapped_keywords = defaultdict(int)

    total_records = 0
    tcfd_related_count = 0

    with open(results_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total_records += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            is_tcfd_related = record.get("is_tcfd_related", False)
            if not is_tcfd_related:
                continue

            tcfd_related_count += 1
            keyword_a = record.get("keyword_a", "")
            file_field = record.get("file", "")

            # Strip .md from filename
            if file_field.endswith(".md"):
                filename = file_field[:-3]
            else:
                filename = file_field

            # Look up dimension for keyword_a
            dimension = keyword_dim_map.get(keyword_a, "")
            if not dimension:
                unmapped_keywords[keyword_a] += 1
                continue

            counts[(filename, dimension)] += 1

    year_stats = {
        "total_records": total_records,
        "tcfd_related": tcfd_related_count,
        "mapped": sum(counts.values()),
        "unmapped": sum(unmapped_keywords.values()),
    }

    return dict(counts), dict(unmapped_keywords), year_stats


def merge_llm_stats(
    keyword_dim_map: dict[str, str],
    evaluate_cooccurrence_dir: Path,
    output_frequency_dir: Path,
    num_workers: int = 16,
) -> tuple[dict[str, int], dict[str, int]]:
    """Merge LLM stats into existing frequency CSVs.

    Args:
        keyword_dim_map: Mapping of keyword -> dimension
        evaluate_cooccurrence_dir: Directory containing year subdirectories with results.jsonl
        output_frequency_dir: Directory containing 词频统计_{政策,市场,技术}.csv
        num_workers: Number of parallel workers (default: 16)

    Returns:
        Tuple of (all_unmapped_keywords, all_year_stats) where:
        - all_unmapped_keywords: dict mapping keyword -> total count across all years
        - all_year_stats: dict mapping year -> per-year stats dict
    """
    # Find all year directories
    year_dirs = []
    for item in sorted(evaluate_cooccurrence_dir.iterdir()):
        if item.is_dir() and item.name.isdigit():
            year_dirs.append(item)

    print(f"Found {len(year_dirs)} year directories to process")

    # Process year directories in parallel using ThreadPoolExecutor
    args_list = [(year_dir, keyword_dim_map) for year_dir in year_dirs]

    all_counts = {}
    all_unmapped = defaultdict(int)
    all_year_stats = {}

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(process_year_directory, args): args for args in args_list}
        for future in as_completed(futures):
            args = futures[future]
            year_dir = args[0]
            counts, unmapped, year_stats = future.result()
            all_counts.update(counts)

            # Aggregate unmapped keywords
            for kw, cnt in unmapped.items():
                all_unmapped[kw] += cnt

            # Store per-year stats
            all_year_stats[year_dir.name] = year_stats

            # Print per-year stats
            print(f"\n=== {year_dir.name} 年 ===")
            print(f"  总记录数: {year_stats['total_records']}")
            print(f"  TCFD相关: {year_stats['tcfd_related']}")
            print(f"  成功映射: {year_stats['mapped']}")
            print(f"  未映射词: {year_stats['unmapped']}")
            if unmapped:
                top_unmapped = sorted(unmapped.items(), key=lambda x: -x[1])[:10]
                print(f"  未映射词Top10: {dict(top_unmapped)}")

    print(f"\nAggregated {len(all_counts)} (filename, dimension) pairs")

    # Load existing CSVs and merge
    dim_csv_names = {
        "政策": "词频统计_政策.csv",
        "市场": "词频统计_市场.csv",
        "技术": "词频统计_技术.csv",
    }

    for dimension, csv_name in dim_csv_names.items():
        csv_path = output_frequency_dir / csv_name
        if not csv_path.exists():
            print(f"Warning: CSV not found {csv_path}, skipping")
            continue

        df = pd.read_csv(csv_path, encoding="utf-8-sig")

        # Initialize new columns
        df["llm_sum_class_AB"] = 0
        df["llm_sum_class_AB_每万字"] = 0.0

        # Merge counts
        merged_count = 0
        for (filename, dim), count in all_counts.items():
            if dim != dimension:
                continue

            mask = df["filename"] == filename
            if mask.any():
                # Get report_words_count for normalization
                words_count = df.loc[mask, "report_words_count"].values[0]
                if words_count and words_count > 0:
                    normalized = round(count / words_count * 10000, 4)
                else:
                    normalized = 0.0

                df.loc[mask, "llm_sum_class_AB"] = count
                df.loc[mask, "llm_sum_class_AB_每万字"] = normalized
                merged_count += 1

        print(
            f"Dimension {dimension}: merged {merged_count} records into {csv_path.name}"
        )

        # Save updated CSV
        df.to_csv(csv_path, encoding="utf-8-sig", index=False)
        print(f"Saved: {csv_path}")

    # Print summary of all unmapped keywords
    if all_unmapped:
        print(f"\n=== 全局未映射词 (共 {len(all_unmapped)} 个) ===")
        sorted_unmapped = sorted(all_unmapped.items(), key=lambda x: -x[1])
        for kw, cnt in sorted_unmapped:
            print(f"  {kw}: {cnt}")
    else:
        print("\n=== 全局未映射词: 无 ===")

    return dict(all_unmapped), all_year_stats


def main():
    parser = argparse.ArgumentParser(
        description="Merge LLM-validated cooccurrence stats into frequency CSVs"
    )
    parser.add_argument(
        "--tcfd-validated",
        type=str,
        default="doc/word-bags/tcfd-validated/tcfd_llm_validated.json",
        help="Path to tcfd_llm_validated.json",
    )
    parser.add_argument(
        "--evaluate-cooccurrence-dir",
        type=str,
        default="output/evaluate_cooccurrence",
        help="Directory containing year subdirectories with results.jsonl",
    )
    parser.add_argument(
        "--output-frequency-dir",
        type=str,
        default="output/frequency",
        help="Directory containing 词频统计_*.csv files",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of parallel workers (default: CPU count)",
    )
    args = parser.parse_args()

    tcfd_validated_path = Path(args.tcfd_validated)
    evaluate_cooccurrence_dir = Path(args.evaluate_cooccurrence_dir)
    output_frequency_dir = Path(args.output_frequency_dir)

    if not tcfd_validated_path.exists():
        print(f"Error: File not found at {tcfd_validated_path}")
        return

    print(f"Loading keyword -> dimension mapping from {tcfd_validated_path}")
    keyword_dim_map = load_keyword_dimension_mapping(tcfd_validated_path)
    print(f"Built mapping for {len(keyword_dim_map)} keywords")

    print(f"\nProcessing year directories in {evaluate_cooccurrence_dir}")
    merge_llm_stats(
        keyword_dim_map=keyword_dim_map,
        evaluate_cooccurrence_dir=evaluate_cooccurrence_dir,
        output_frequency_dir=output_frequency_dir,
        num_workers=args.workers,
    )

    print("\nDone!")


if __name__ == "__main__":
    main()
