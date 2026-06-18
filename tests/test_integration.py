# tests/test_integration.py
"""集成测试 - 需要SGLang服务运行"""
import pytest
from pathlib import Path

from tcfd_extractor import (
    load_word_bag,
    read_text_with_fallback,
    check_sglang_health,
    SmartChunker,
    TCFDKeywordExtractor,
    AnnualReportSampler,
    ResultAggregator
)


@pytest.mark.skipif(
    not check_sglang_health("http://127.0.0.1:30000/v1"),
    reason="SGLang服务不可用"
)
def test_full_pipeline():
    """测试完整流程"""
    # 1. 加载词袋
    word_bag = load_word_bag("doc/word-bags/raw/words_bag.md")
    assert len(word_bag["政策维度"]) > 0

    # 2. 采样
    sampler = AnnualReportSampler("/home/bo/projects/data/A股年报", sample_size=2)
    reports = sampler.random_sample(years=(2023, 2024))
    assert len(reports) > 0

    # 3. 读取文本
    text = read_text_with_fallback(reports[0])
    assert len(text) > 0

    # 4. 分块
    chunker = SmartChunker(min_chunk_size=200, max_chunk_size=1000)
    chunks = chunker.chunk_by_paragraph(text, target_size=500)
    assert len(chunks) > 0

    # 5. 提取
    extractor = TCFDKeywordExtractor()
    result = extractor.extract(chunks[0], word_bag)
    assert "政策维度" in result
    assert "市场维度" in result
    assert "技术维度" in result

    # 6. 聚合
    aggregator = ResultAggregator(word_bag)
    aggregated = aggregator.aggregate([result])
    assert isinstance(aggregated, dict)
