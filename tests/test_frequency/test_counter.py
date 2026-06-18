import pytest
from tcfd_extractor.frequency.counter import count_keywords, get_word_count


def test_count_single_keyword():
    """测试单关键词统计"""
    text = "碳达峰和碳中和是重要目标，碳达峰是第一步"
    keywords = ["碳达峰", "碳中和"]
    result = count_keywords(text, keywords)
    assert result["碳达峰"] == 2
    assert result["碳中和"] == 1


def test_count_normalized():
    """测试归一化"""
    text = "碳达峰" * 100  # 100次 = 300字 (每个词3个字)
    keywords = ["碳达峰"]
    result = count_keywords(text, keywords, normalize=True)
    # 100次 / (300/10000) = 100 / 0.03 = 3333.33
    assert result["碳达峰_每万字"] == 3333.3333


def test_get_word_count():
    """测试字数统计"""
    text = "Hello World"
    assert get_word_count(text) == 11
