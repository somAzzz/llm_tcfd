"""批量评估共现上下文(消除 subprocess,纯函数式)

按年份分别评估 cooccurrence_context 目录下的内容。

Examples:
    # 评估所有年份
    python -m tcfd_extractor.evaluation.batch_evaluate_cooccurrence

    # 指定年份
    python -m tcfd_extractor.evaluation.batch_evaluate_cooccurrence \\
        --year 2020
"""
import argparse
import logging
import sys
from pathlib import Path

from ..config import BatchSettings, LLMSettings, batch_settings, llm_settings
from .batch import BatchEvaluator
from .evaluator import CooccurrenceEvaluator
from .exceptions import LLMEvaluationError
from .summary import compute_statistics, generate_summary


logger = logging.getLogger(__name__)


def main() -> int:
    """CLI 主入口。返回退出码。"""
    try:
        return _main_impl()
    except Exception as e:
        logger.exception("CLI 顶层异常: %s", e)
        return 1


def _main_impl() -> int:
    parser = argparse.ArgumentParser(description="批量评估共现上下文(按年份)")
    parser.add_argument(
        "--input-dir", type=str,
        default="output/frequency/cooccurrence_context",
        help="共现上下文 MD 文件根目录",
    )
    parser.add_argument(
        "--output-dir", type=str,
        default="output/evaluate_cooccurrence",
        help="评估结果输出根目录",
    )
    parser.add_argument(
        "--year", type=str,
        default=None,
        help="指定单个年份(默认遍历所有年份)",
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
        help="并发评估数(默认用全局 config)",
    )
    args = parser.parse_args()

    # 显式 logging 配置
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    input_root = Path(args.input_dir)
    output_root = Path(args.output_dir)

    if not input_root.exists():
        logger.error("输入目录不存在: %s", input_root)
        return 1

    # 获取所有年份子目录
    year_dirs = sorted(
        [d for d in input_root.iterdir() if d.is_dir() and d.name.isdigit()]
    )
    if not year_dirs:
        logger.warning("在 %s 中未找到年份子目录,处理根目录", input_root)
        year_dirs = [input_root]

    if args.year:
        year_dirs = [d for d in year_dirs if d.name == args.year]
        if not year_dirs:
            logger.error("未找到指定年份: %s", args.year)
            return 1

    logger.info("发现 %d 个年份目录", len(year_dirs))

    # 构造 settings(CLI 参数覆盖)
    settings = LLMSettings(
        base_url=args.api_url,
        model_name=args.model,
    )
    batch_cfg = BatchSettings(
        workers=args.workers,
        max_retries=batch_settings.max_retries,
        retry_delay=batch_settings.retry_delay,
        reason_max_length=batch_settings.reason_max_length,
    )
    evaluator = CooccurrenceEvaluator(settings=settings)

    # 每个年份独立处理(避免 BatchEvaluator 跨年状态泄漏)
    failed_years = []
    for year_dir in year_dirs:
        year = year_dir.name
        logger.info("=" * 50)
        logger.info("处理年份: %s", year)
        logger.info("=" * 50)

        year_output_dir = output_root / year
        year_output_dir.mkdir(parents=True, exist_ok=True)
        results_file = year_output_dir / "results.jsonl"
        summary_file = year_output_dir / "summary.md"

        # 每年重新实例化 BatchEvaluator(spec 风险缓解)
        batch_evaluator = BatchEvaluator(evaluator, settings=batch_cfg)

        try:
            stats = batch_evaluator.evaluate_all(year_dir, results_file)
            logger.info(
                "%s: %d 片段, %d TCFD 相关, %d 解析错误, %d 评估错误",
                year, stats["total"], stats["tcfd_count"],
                stats["parse_errors"], stats["eval_errors"]
            )
        except LLMEvaluationError as e:
            logger.exception("年份 %s 评估失败: %s", year, e)
            failed_years.append(year)
            continue

        try:
            statistics = compute_statistics(results_file)
            generate_summary(statistics, summary_file, settings=settings)
        except LLMEvaluationError as e:
            logger.exception("年份 %s 总结失败: %s", year, e)
            failed_years.append(year)

    if failed_years:
        logger.error("失败的年份: %s", failed_years)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())