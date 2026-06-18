import pytest
from tcfd_extractor.evaluator import ChunkEvaluator

def test_evaluator_init():
    """测试评估器初始化"""
    word_bag = {
        "政策维度": ["碳达峰", "碳中和"],
        "市场维度": ["碳交易", "绿色信贷"],
        "技术维度": ["低碳技术", "节能技术"]
    }
    evaluator = ChunkEvaluator(word_bag)
    assert evaluator.word_bag == word_bag

def test_calculate_f1():
    """测试F1计算"""
    word_bag = {
        "政策维度": ["碳达峰", "碳中和"],
        "市场维度": ["碳交易"],
        "技术维度": []
    }
    evaluator = ChunkEvaluator(word_bag)
    result = evaluator.calculate_f1(["碳达峰", "碳中和", "新词"])
    assert result["extracted_count"] == 3
    assert result["matched_count"] == 2
    assert result["precision"] > 0
