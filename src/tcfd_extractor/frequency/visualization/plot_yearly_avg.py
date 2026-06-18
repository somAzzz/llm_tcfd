#!/usr/bin/env python3
"""Plot yearly average llm_sum_class_AB per 10k chars for 3 TCFD dimensions

Examples:
    python -m tcfd_extractor.frequency.visualization.plot_yearly_avg
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def load_dim_csv(csv_path: Path, dim_name: str, value_col: str) -> pd.DataFrame:
    """Load dimension CSV, compute yearly average of value_col"""
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    yearly = df.groupby("year")[value_col].mean().reset_index()
    yearly.columns = ["year", dim_name]
    yearly["year"] = yearly["year"].astype(int)
    return yearly


def main():
    parser = argparse.ArgumentParser(description="Plot yearly dimension averages")
    parser.add_argument(
        "--input-dir",
        type=str,
        default="output/frequency",
        help="Directory containing frequency CSV files",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output/frequency/dimension_yearly_avg.png",
        help="Output image path",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="Image DPI",
    )
    parser.add_argument(
        "--value-col",
        type=str,
        default="llm_sum_class_AB_每万字",
        help="CSV column to plot (default: llm_sum_class_AB_每万字)",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)

    # Dimension mapping: display_name -> csv_filename
    dims = {
        "Policy": input_dir / "词频统计_政策.csv",
        "Market": input_dir / "词频统计_市场.csv",
        "Technology": input_dir / "词频统计_技术.csv",
    }

    # Load and merge data
    dfs = []
    for dim_name, csv_path in dims.items():
        if not csv_path.exists():
            print(f"Warning: File not found {csv_path}, skipping")
            continue
        df = load_dim_csv(csv_path, dim_name, args.value_col)
        dfs.append(df)
        print(f"Loaded {dim_name}: {len(df)} records")

    if not dfs:
        print("Error: No CSV files available")
        return

    # Merge by year
    merged = dfs[0]
    for df in dfs[1:]:
        merged = pd.merge(merged, df, on="year", how="outer")

    merged = merged.sort_values("year")

    print(f"\nYear range: {merged['year'].min()} - {merged['year'].max()}")
    print(merged.to_string(index=False))

    # Compute yearly average
    yearly_avg = merged.groupby("year").mean(numeric_only=True)

    # Plot
    fig, ax = plt.subplots(figsize=(12, 6))

    colors = ["#e74c3c", "#27ae60", "#3498db"]  # red, green, blue
    markers = ["o", "s", "^"]

    for i, col in enumerate(yearly_avg.columns):
        ax.plot(
            yearly_avg.index,
            yearly_avg[col],
            label=col,
            color=colors[i % len(colors)],
            marker=markers[i % len(markers)],
            linewidth=2,
            markersize=5,
        )

    ax.set_xlabel("Year", fontsize=12)
    # Translate Chinese column name to English for display
    ylabel_map = {
        "llm_sum_class_AB_每万字": "LLM sum_class_AB per 10k chars",
        "sum_class_AB_每万字": "sum_class_AB per 10k chars",
    }
    ylabel_display = ylabel_map.get(args.value_col, args.value_col)
    ax.set_ylabel(f"{ylabel_display} (yearly avg)", fontsize=12)
    ax.set_title("TCFD Keyword Co-occurrence Intensity by Year (LLM Validated)", fontsize=14, fontweight="bold")
    ax.legend(title="Dimension", loc="upper left")
    ax.grid(True, alpha=0.3)
    ax.set_xticks(yearly_avg.index)
    ax.tick_params(axis="x", rotation=45)

    plt.tight_layout()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=args.dpi, bbox_inches="tight")
    print(f"\nImage saved: {output_path}")


if __name__ == "__main__":
    main()
