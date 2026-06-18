"""共现上下文评估CLI

Examples:
    # 评估共现上下文
    python -m tcfd_extractor.evaluation.evaluate_cooccurrence \\
        --input-dir output/sample_100/cooccurrence_context \\
        --output output/evaluate_cooccurrence/results.jsonl
"""

import argparse
from pathlib import Path

from tcfd_extractor.evaluation.cooccurrence_evaluator import (
    CooccurrenceEvaluator,
    BatchEvaluator,
    generate_summary,
)


def main():
    parser = argparse.ArgumentParser(description="TCFD共现上下文评估")
    parser.add_argument(
        "--input-dir",
        type=str,
        default="output/sample_100/cooccurrence_context",
        help="共现上下文MD文件目录",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output/evaluate_cooccurrence/results.jsonl",
        help="评估结果JSONL文件",
    )
    parser.add_argument(
        "--summary",
        type=str,
        default="output/evaluate_cooccurrence/summary.md",
        help="总结报告文件",
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

    input_dir = Path(args.input_dir)
    output_file = Path(args.output)
    summary_file = Path(args.summary)

    print(f"输入目录: {input_dir}")
    print(f"输出文件: {output_file}")

    # 评估
    evaluator = CooccurrenceEvaluator(base_url=args.api_url, model_name=args.model)
    batch_evaluator = BatchEvaluator(evaluator, workers=args.workers)

    stats = batch_evaluator.evaluate_all(input_dir, output_file)

    print(f"\n评估完成: {stats['total']} 片段, {stats['tcfd_count']} TCFD相关")

    # 生成总结
    if summary_file:
        generate_summary(output_file, summary_file, args.api_url, args.model)


if __name__ == "__main__":
    main()