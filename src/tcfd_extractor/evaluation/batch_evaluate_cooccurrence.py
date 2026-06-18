#!/usr/bin/env python3
"""批量评估共现上下文

按年份分别评估 cooccurrence_context 目录下的内容

Examples:
    # 评估所有年份
    python scripts/batch_evaluate_cooccurrence.py

    # 指定输入输出目录
    python scripts/batch_evaluate_cooccurrence.py \\
        --input-dir output/frequency/cooccurrence_context \\
        --output-dir output/evaluate_cooccurrence
"""

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


def print_results_stats(results_file: Path) -> None:
    """Print statistics from results.jsonl file."""
    if not results_file.exists():
        print(f"  [统计] 结果文件不存在: {results_file}")
        return

    total = 0
    tcfd_related = 0
    keyword_a_counts = Counter()
    keyword_b_counts = Counter()
    file_counts = Counter()

    with open(results_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            total += 1
            if record.get("is_tcfd_related"):
                tcfd_related += 1

            keyword_a = record.get("keyword_a", "")
            keyword_b = record.get("keyword_b", "")
            file_field = record.get("file", "")

            if keyword_a:
                keyword_a_counts[keyword_a] += 1
            if keyword_b:
                keyword_b_counts[keyword_b] += 1
            if file_field:
                file_counts[file_field] += 1

    print(f"\n  [统计] {results_file.parent.name} 年度结果:")
    print(f"  {'=' * 40}")
    print(f"  总记录数: {total}")
    print(f"  TCFD相关: {tcfd_related} ({tcfd_related/total*100:.1f}%)" if total > 0 else "  TCFD相关: 0")
    print(f"  涉及公司数: {len(file_counts)}")
    print(f"  不同关键词A数: {len(keyword_a_counts)}")
    print(f"  不同关键词B数: {len(keyword_b_counts)}")

    if keyword_a_counts:
        top_a = keyword_a_counts.most_common(5)
        print(f"  Top5 关键词A: {', '.join([f'{k}({v})' for k, v in top_a])}")

    print()


def main():
    parser = argparse.ArgumentParser(description="批量评估共现上下文（按年份）")
    parser.add_argument(
        "--input-dir",
        type=str,
        default="output/frequency/cooccurrence_context",
        help="共现上下文MD文件根目录",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output/evaluate_cooccurrence",
        help="评估结果输出根目录",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default="http://127.0.0.1:30000/v1",
        help="SGLang API端点",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="Qwen/Qwen3.5-35B-A3B",
        help="模型名称",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="并发评估数，默认8",
    )
    args = parser.parse_args()

    input_root = Path(args.input_dir)
    output_root = Path(args.output_dir)

    if not input_root.exists():
        print(f"错误: 输入目录不存在: {input_root}")
        sys.exit(1)

    # 获取所有年份子目录
    year_dirs = sorted(
        [d for d in input_root.iterdir() if d.is_dir() and d.name.isdigit()]
    )

    if not year_dirs:
        print(f"警告: 在 {input_root} 中未找到年份子目录")
        # 退化为直接处理根目录
        year_dirs = [input_root]
        input_root_should_be_year = False
    else:
        input_root_should_be_year = True

    print(f"发现 {len(year_dirs)} 个年份目录\n")

    for year_dir in year_dirs:
        year = (
            year_dir.name if input_root_should_be_year else input_root.name or "unknown"
        )
        print(f"{'=' * 50}")
        print(f"处理年份: {year}")
        print(f"{'=' * 50}")

        # 构建输出路径
        year_output_dir = output_root / year
        year_output_dir.mkdir(parents=True, exist_ok=True)

        results_file = year_output_dir / "results.jsonl"
        summary_file = year_output_dir / "summary.md"

        # 确定输入目录
        input_dir = year_dir if input_root_should_be_year else input_root

        # 构建命令
        cmd = [
            sys.executable,
            "-m",
            "tcfd_extractor.evaluation.evaluate_cooccurrence",
            "--input-dir",
            str(input_dir),
            "--output",
            str(results_file),
            "--summary",
            str(summary_file),
            "--api-url",
            args.api_url,
            "--model",
            args.model,
            "--workers",
            str(args.workers),
        ]

        print(f"输入: {input_dir}")
        print(f"输出: {results_file}")
        print(f"命令: {' '.join(cmd)}\n")

        # 执行评估
        result = subprocess.run(cmd, check=False)

        if result.returncode != 0:
            print(f"错误: 年份 {year} 评估失败，退出码: {result.returncode}")
            # 继续处理其他年份
        else:
            print_results_stats(results_file)
            print(f"完成: {year}\n")


if __name__ == "__main__":
    main()
