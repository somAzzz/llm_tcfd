#!/usr/bin/env python3
"""Resolve duplicate TCFD keywords using LLM judgment - optimized version.

Optimizations:
- Simplified prompt (only keyword + options)
- Parallel processing with ThreadPoolExecutor
- Batch API support for OpenAI-compatible endpoints
"""

import argparse
import json
import re
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional
from openai import OpenAI

# ==============================================================================
# System Prompt (preserved)
# ==============================================================================
SYSTEM_PROMPT = """你是TCFD关键词分类专家。TCFD框架有三个维度：
- 政策（Policy）：政府法规、碳交易、环境合规、补贴政策等
- 市场（Market）：碳金融、绿色产品、ESG、绿色电力交易等
- 技术（Technology）：低碳技术、新能源、节能、储能等

请根据每个分类的语义，判断关键词最应该属于哪个分类。
注意：
1. 选择语义最契合的分类
2. 只输出选项编号（如"1"），不要输出其他内容
"""


@dataclass
class LLMJudgmentResult:
    """Result of LLM judgment for a single keyword."""
    keyword: str
    locations: list[tuple[str, str]]
    selected_index: Optional[int]  # 0-based index
    selected_category: str  # "维度/分类" format
    error: Optional[str] = None


def parse_duplicates_file(file_path: Path) -> dict[str, list[tuple[str, str]]]:
    """Parse duplicates file to extract keyword -> [(dimension, category), ...] mapping."""
    keyword_locations = {}
    current_keyword = None

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("关键词:"):
                current_keyword = stripped.replace("关键词:", "").strip()
                if current_keyword not in keyword_locations:
                    keyword_locations[current_keyword] = []
            elif stripped.startswith("- "):
                location = stripped.replace("- ", "")
                if "/" in location:
                    parts = location.split("/")
                    if len(parts) == 2:
                        dimension = parts[0].strip()
                        category = parts[1].strip()
                        if current_keyword:
                            keyword_locations[current_keyword].append((dimension, category))

    return keyword_locations


def load_tcfd_json(file_path: Path) -> dict:
    """Load and return tcfd_validated JSON structure."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_keyword_index(data: dict) -> dict[str, list[tuple[str, str]]]:
    """Build index of keyword -> [(dimension, category), ...] from original JSON."""
    keyword_index = {}

    for dimension in ["政策", "市场", "技术"]:
        if dimension not in data:
            continue
        for category, keywords in data[dimension].items():
            for keyword in keywords:
                if keyword not in keyword_index:
                    keyword_index[keyword] = []
                keyword_index[keyword].append((dimension, category))

    return keyword_index


def build_simple_user_prompt(keyword: str, locations: list[tuple[str, str]]) -> str:
    """Build simplified user prompt with only keyword and options."""
    options = "\n".join([f"{i + 1}. {dim} / {cat}" for i, (dim, cat) in enumerate(locations)])
    return f'关键词"{keyword}"出现在以下分类中：\n{options}\n\n请判断最应该属于哪个分类，输出选项编号（如1）：'


def parse_llm_response(response: str, num_options: int) -> tuple[Optional[int], Optional[str]]:
    """Parse LLM response to extract option index.

    Returns:
        (selected_index, error_message)
        selected_index is 0-based, or None if invalid
    """
    response = response.strip()

    # Try direct number first
    try:
        idx = int(response) - 1  # Convert to 0-based
        if 0 <= idx < num_options:
            return idx, None
    except ValueError:
        pass

    # Try to extract number from response
    match = re.search(r"(\d+)", response)
    if match:
        idx = int(match.group(1)) - 1
        if 0 <= idx < num_options:
            return idx, None

    return None, f"Invalid response: {response}"


def call_llm_judgment(
    client: OpenAI,
    model: str,
    keyword: str,
    locations: list[tuple[str, str]],
    max_retries: int = 3,
    verbose: bool = False,
) -> LLMJudgmentResult:
    """Call LLM to judge which category the keyword belongs to."""
    user_prompt = build_simple_user_prompt(keyword, locations)
    valid_options = [f"{dim}/{cat}" for dim, cat in locations]

    # Build full prompt for logging
    full_prompt = f"[SYSTEM]\n{SYSTEM_PROMPT}\n\n[USER]\n{user_prompt}"
    if verbose:
        print(f"\n{'='*60}")
        print(f"Keyword: {keyword}")
        print(f"Locations: {locations}")
        print(f"{'='*60}")
        print(full_prompt)
        print(f"{'='*60}\n")

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
            )

            result = response.choices[0].message.content.strip()
            selected_index, error = parse_llm_response(result, len(locations))

            if selected_index is not None:
                return LLMJudgmentResult(
                    keyword=keyword,
                    locations=locations,
                    selected_index=selected_index,
                    selected_category=valid_options[selected_index],
                    error=None,
                )

            error_msg = error or f"Invalid response: {result}"

        except Exception as e:
            error_msg = str(e)

        if attempt < max_retries - 1:
            delay = 2 ** attempt * 0.5  # Shorter delay: 0.5s, 1s, 2s
            time.sleep(delay)

    return LLMJudgmentResult(
        keyword=keyword,
        locations=locations,
        selected_index=None,
        selected_category="",
        error=error_msg,
    )


def process_keyword(
    args_tuple: tuple,
) -> LLMJudgmentResult:
    """Worker function for parallel processing."""
    client, model, keyword, locations, verbose = args_tuple
    return call_llm_judgment(client, model, keyword, locations, verbose=verbose)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Resolve duplicate TCFD keywords using LLM (optimized)"
    )
    parser.add_argument(
        "--input-json",
        type=str,
        default="doc/word-bags/tcfd-validated/tcfd_validated.json",
        help="Input TCFD validated JSON"
    )
    parser.add_argument(
        "--duplicates-file",
        type=str,
        required=True,
        help="Duplicates analysis file path"
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default="doc/word-bags/tcfd-validated/tcfd_llm_validated.json",
        help="Output deduplicated JSON"
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://127.0.0.1:30000/v1",
        help="LLM API base URL"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="Qwen/Qwen3.5-35B-A3B",
        help="LLM model name"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Number of parallel workers"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print full prompts for debugging"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Load duplicates
    duplicates_path = Path(args.duplicates_file)
    if not duplicates_path.exists():
        print(f"Error: Duplicates file not found: {duplicates_path}")
        return

    keyword_locations = parse_duplicates_file(duplicates_path)
    print(f"\nParsed {len(keyword_locations)} duplicate keywords")

    # Load original JSON
    input_path = Path(args.input_json)
    if not input_path.exists():
        print(f"Error: Input JSON not found: {input_path}")
        return

    data = load_tcfd_json(input_path)
    keyword_index = build_keyword_index(data)
    print(f"Loaded JSON with {len(data)} dimensions, {len(keyword_index)} keywords")

    # Initialize LLM client
    client = OpenAI(base_url=args.base_url, api_key="sk-local")

    # Prepare tasks for parallel execution
    total = len(keyword_locations)
    tasks = [
        (client, args.model, keyword, locations, args.verbose)
        for keyword, locations in keyword_locations.items()
    ]

    # Process in parallel
    decisions = {}
    failed_count = 0
    completed = 0

    print(f"\nProcessing {total} duplicate keywords with LLM ({args.workers} workers)...")

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process_keyword, task): task for task in tasks}

        for future in as_completed(futures):
            completed += 1
            result = future.result()

            if result.selected_index is not None:
                decisions[result.keyword] = result.selected_category
            else:
                # Use fallback (first occurrence in original index)
                if result.keyword in keyword_index:
                    first_loc = keyword_index[result.keyword][0]
                    fallback = f"{first_loc[0]}/{first_loc[1]}"
                else:
                    fallback = ""
                decisions[result.keyword] = fallback
                failed_count += 1
                print(f"    Failed ({result.error}): {result.keyword} -> fallback: {fallback}")

            if completed % 20 == 0 or completed == total:
                elapsed = time.time() - start_time
                rate = completed / elapsed
                eta = (total - completed) / rate if rate > 0 else 0
                print(f"  Processed {completed}/{total}... ({rate:.1f}/s, ETA: {eta:.0f}s)")

    elapsed = time.time() - start_time
    print(f"\nLLM decisions complete. {len(decisions)} keywords in {elapsed:.1f}s ({len(decisions)/elapsed:.1f}/s)")

    # Generate output JSON
    print("\nGenerating output JSON...")

    # Count keywords in original
    original_count = sum(
        len(kws) for categories in data.values() for kws in categories.values()
    )

    # Build deduplicated output
    output_data = {}
    kept_count = 0
    removed_count = 0

    for dimension, categories in data.items():
        output_data[dimension] = {}
        for category, keywords in categories.items():
            dim_cat = f"{dimension}/{category}"
            kept = []
            for kw in keywords:
                if kw in decisions:
                    # This is a duplicate - only keep if this is the chosen location
                    if decisions[kw] == dim_cat:
                        kept.append(kw)
                        kept_count += 1
                    else:
                        removed_count += 1
                else:
                    # Not a duplicate - keep as is
                    kept.append(kw)
                    kept_count += 1

            if kept:
                output_data[dimension][category] = kept

    # Count output keywords
    output_count = sum(
        len(kws) for categories in output_data.values() for kws in categories.values()
    )

    # Save output
    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"Saved: {output_path}")

    # Summary
    print(f"\n=== Summary ===")
    print(f"Original keywords: {original_count}")
    print(f"Output keywords: {output_count}")
    print(f"Duplicates removed: {removed_count}")
    print(f"Keywords kept: {kept_count}")
    print(f"LLM failures (used fallback): {failed_count}")
    print(f"Total time: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
