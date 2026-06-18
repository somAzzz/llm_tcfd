"""TCFD关键词提取器"""

from .sampler import AnnualReportSampler
from .chunker import SmartChunker
from .extractor import (
    TCFDKeywords,
    load_word_bag,
    read_text_with_fallback,
    retry_on_failure,
    check_sglang_health,
    TCFDKeywordExtractor
)
from .executor import ControlledExecutor
from .evaluator import ChunkEvaluator
from .aggregator import ResultAggregator

__version__ = "0.1.0"
__all__ = [
    "AnnualReportSampler",
    "SmartChunker",
    "TCFDKeywords",
    "load_word_bag",
    "read_text_with_fallback",
    "retry_on_failure",
    "check_sglang_health",
    "TCFDKeywordExtractor",
    "ControlledExecutor",
    "ChunkEvaluator",
    "ResultAggregator",
]
