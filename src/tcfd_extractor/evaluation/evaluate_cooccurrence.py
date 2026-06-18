"""共现上下文评估 CLI

Examples:
    # 评估某年份
    python -m tcfd_extractor.evaluation.evaluate_cooccurrence \\
        --input-dir output/frequency/cooccurrence_context/2020 \\
        --output output/evaluate_cooccurrence/2020/results.jsonl \\
        --summary output/evaluate_cooccurrence/2020/summary.md

    # 评估整批(用全局 config 默认值)
    python -m tcfd_extractor.evaluation.evaluate_cooccurrence
"""
import argparse
import logging
import sys
from pathlib import Path

from ..config import BatchSettings, LLMSettings, batch_settings, llm_settings, path_settings
from .batch import BatchEvaluator
from .evaluator import CooccurrenceEvaluator
from .exceptions import LLMEvaluationError
from .summary import compute_statistics, generate_summary


logger = logging.getLogger(__name__)


def _get_default_input_dir() -> Path:
    return path_settings.input_root


def _get_default_output_dir() -> Path:
    return path_settings.output_root


def build_arg_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器(默认值从全局 config 读取)"""
    parser = argparse.ArgumentParser(
        description="TCFD 共现上下文评估"
    )
    parser.add_argument(
        "--input-dir", type=str,
        default=str(_get_default_input_dir()),
        help="共现上下文 MD 文件目录",
    )
    parser.add_argument(
        "--output", type=str,
        default=str(_get_default_output_dir() / "results.jsonl"),
        help="评估结果 JSONL 文件",
    )
    parser.add_argument(
        "--summary", type=str,
        default=str(_get_default_output_dir() / "summary.md"),
        help="总结报告文件",
    )
    parser.add_argument(
        "--api-url", type=str,
        default=llm_settings.base_url,
        help="SGLang API 端点",
    )
    parser.add_argument(
        "--model", type=str,
        default=llm_settings.model_name,
        help="模型名称",
    )
    parser.add_argument(
        "--workers", type=int,
        default=batch_settings.workers,
        help="并发评估数",
    )
    parser.add_argument(
        "--year", type=str,
        default=None,
        help="指定单个年份(仅对批量模式有意义,本 CLI 单文件模式下保留为占位)",
    )
    return parser


def main() -> int:
    """CLI 主入口。返回退出码。"""
    try:
        return _main_impl()
    except Exception as e:
        logger.exception("CLI 顶层异常: %s", e)
        return 1


def _main_impl() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_file = Path(args.output)
    summary_file = Path(args.summary) if args.summary else None

    # 显式 logging 配置(避免在 lib 引入时副作用)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("输入目录: %s", input_dir)
    logger.info("输出文件: %s", output_file)

    # 构造 settings(CLI 参数覆盖全局默认值)
    settings = LLMSettings(
        base_url=args.api_url,
        model_name=args.model,
    )
    # CLI 传入的 workers 覆盖全局 batch_settings
    batch_cfg = BatchSettings(
        workers=args.workers,
        max_retries=batch_settings.max_retries,
        retry_delay=batch_settings.retry_delay,
        reason_max_length=batch_settings.reason_max_length,
    )

    evaluator = CooccurrenceEvaluator(settings=settings)
    batch_evaluator = BatchEvaluator(evaluator, settings=batch_cfg)

    try:
        stats = batch_evaluator.evaluate_all(input_dir, output_file)
        logger.info(
            "评估完成: %d 片段, %d TCFD 相关, %d 解析错误, %d 评估错误",
            stats["total"], stats["tcfd_count"],
            stats["parse_errors"], stats["eval_errors"]
        )
    except LLMEvaluationError as e:
        logger.exception("LLM 评估失败: %s", e)
        return 1

    if summary_file:
        try:
            statistics = compute_statistics(output_file)
            generate_summary(statistics, summary_file, settings=settings)
        except LLMEvaluationError as e:
            logger.exception("总结生成失败: %s", e)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())