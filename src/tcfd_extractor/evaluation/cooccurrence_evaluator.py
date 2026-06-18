"""向后兼容的 re-export 入口。

原始 468 行文件已拆分为:
  - models (Pydantic 数据模型)
  - parser (Markdown 解析)
  - prompts (LLM 提示词常量)
  - evaluator (CooccurrenceEvaluator)
  - batch (BatchEvaluator)
  - summary (compute_statistics + generate_summary)
  - exceptions (自定义异常)

本文件仅作为公开 API 的 re-export,保证现有 16 个测试和外部 import 无需修改。
新代码应直接 import 新的子模块。
"""
from pathlib import Path

from .batch import BatchEvaluator
from .evaluator import CooccurrenceEvaluator
from .exceptions import (
    EvaluationError,
    LLMResponseParseError,
    LLMEvaluationError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from .models import (
    CooccurrenceContext,
    EvaluationResult,
    FileParseResult,
    TCFDValidationResult,
)
from .parser import parse_cooccurrence_md
from .prompts import (
    EVAL_SYSTEM_PROMPT,
    EVAL_USER_PROMPT,
    SUMMARY_SYSTEM_PROMPT,
    SUMMARY_USER_PROMPT,
)
from .summary import compute_statistics as _compute_statistics
from .summary import generate_summary as _generate_summary


def generate_summary(results_file: Path, summary_file: Path):
    """向后兼容包装: 旧 API `generate_summary(results_file, summary_file)`。

    新代码应使用:
        stats = compute_statistics(results_file)
        generate_summary(stats, summary_file)
    """
    stats = _compute_statistics(results_file)
    _generate_summary(stats, summary_file)
    return stats


__all__ = [
    # 数据模型
    "CooccurrenceContext",
    "TCFDValidationResult",
    "EvaluationResult",
    "FileParseResult",
    # 解析
    "parse_cooccurrence_md",
    # 评估器
    "CooccurrenceEvaluator",
    "BatchEvaluator",
    # 总结
    "compute_statistics",
    "generate_summary",
    # 异常
    "EvaluationError",
    "LLMEvaluationError",
    "LLMUnavailableError",
    "LLMResponseParseError",
    "LLMTimeoutError",
    # 提示词
    "EVAL_SYSTEM_PROMPT",
    "EVAL_USER_PROMPT",
    "SUMMARY_SYSTEM_PROMPT",
    "SUMMARY_USER_PROMPT",
]