import pytest
from tcfd_extractor.extractor import (
    TCFDKeywords,
    load_word_bag,
    read_text_with_fallback,
    retry_on_failure,
    check_sglang_health,
    TCFDKeywordExtractor
)


def test_load_word_bag():
    """测试加载词袋"""
    word_bag = load_word_bag("doc/word-bags/raw/words_bag.md")
    assert "政策维度" in word_bag
    assert "市场维度" in word_bag
    assert "技术维度" in word_bag
    # 验证词袋包含预期数量的关键词
    assert len(word_bag["政策维度"]) > 0
    assert len(word_bag["市场维度"]) > 0
    assert len(word_bag["技术维度"]) > 0


def test_read_text_with_fallback():
    """测试多种编码读取"""
    from pathlib import Path
    content = read_text_with_fallback(Path("doc/word-bags/raw/words_bag.md"))
    assert len(content) > 0
    assert "政策维度" in content
    assert "市场维度" in content
    assert "技术维度" in content


def test_retry_on_failure():
    """测试重试装饰器"""
    call_count = 0

    @retry_on_failure(max_retries=3, delay=1)
    def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise Exception("fail")
        return "success"

    result = flaky_function()
    assert result == "success"
    assert call_count == 2


def test_retry_on_failure_max_retries():
    """测试重试装饰器达到最大重试次数"""
    call_count = 0

    @retry_on_failure(max_retries=3, delay=1)
    def always_fail_function():
        nonlocal call_count
        call_count += 1
        raise ValueError("always fails")

    with pytest.raises(ValueError):
        always_fail_function()
    assert call_count == 3


def test_tcfd_keywords_model():
    """测试TCFDKeywords Pydantic模型"""
    keywords = TCFDKeywords(
        政策维度=["碳交易", "碳税"],
        市场维度=["绿色信贷"],
        技术维度=["低碳技术"]
    )
    assert keywords.政策维度 == ["碳交易", "碳税"]
    assert keywords.市场维度 == ["绿色信贷"]
    assert keywords.技术维度 == ["低碳技术"]


def test_tcfd_keywords_empty():
    """测试TCFDKeywords空值"""
    keywords = TCFDKeywords(
        政策维度=[],
        市场维度=[],
        技术维度=[]
    )
    assert keywords.政策维度 == []
    assert keywords.市场维度 == []
    assert keywords.技术维度 == []


def test_check_sglang_health_invalid_url():
    """测试健康检查无效URL"""
    # 使用一个不存在的服务测试
    result = check_sglang_health("http://invalid.example.com:99999/v1")
    assert result is False


def test_tcfd_keyword_extractor_init():
    """测试TCFDKeywordExtractor初始化"""
    extractor = TCFDKeywordExtractor(
        base_url="http://localhost:8000/v1",
        model_name="test-model"
    )
    assert extractor.client is not None
    assert extractor.model_name == "test-model"
