import pytest
import json
import tempfile
from pathlib import Path
from tcfd_extractor.aggregator import ResultAggregator

def test_aggregator_init():
    """测试聚合器初始化"""
    word_bag = {"政策维度": ["碳达峰"], "市场维度": [], "技术维度": []}
    aggregator = ResultAggregator(word_bag)
    assert aggregator.word_bag == word_bag

def test_aggregate():
    """测试结果聚合"""
    word_bag = {"政策维度": ["碳达峰"], "市场维度": ["碳交易"], "技术维度": []}
    aggregator = ResultAggregator(word_bag)

    chunk_results = [
        {"政策维度": ["碳达峰", "碳中和"], "市场维度": [], "技术维度": []},
        {"政策维度": ["碳达峰"], "市场维度": ["碳交易"], "技术维度": []}
    ]

    result = aggregator.aggregate(chunk_results)
    assert len(result["政策维度"]) == 2  # 去重后
    assert "碳交易" in result["市场维度"]
