"""Tests for frequency main module"""

import json
import tempfile
from pathlib import Path

import pytest

from tcfd_extractor.frequency.main import load_bag_a, count_keywords_v2


class TestLoadBagA:
    """Test load_bag_a function"""

    def test_load_bag_a_returns_dict(self):
        """Test that load_bag_a returns a dictionary"""
        # Create a temporary JSON file with test data
        test_data = {
            "技术": {"低碳": ["碳减排", "节能降碳"], "电动": ["电动车"]},
            "市场": {"碳交易": ["碳市场"]},
            "政策": {"环保": ["环保监管"]}
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(test_data, f)
            temp_path = f.name

        try:
            result = load_bag_a(temp_path)
            assert isinstance(result, dict)
            assert result == test_data
        finally:
            Path(temp_path).unlink()

    def test_load_bag_a_with_single_dim(self):
        """Test loading bag a with single dimension"""
        test_data = {"技术": {"低碳": ["碳减排"]}}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(test_data, f)
            temp_path = f.name

        try:
            result = load_bag_a(temp_path)
            assert result == test_data
            assert "技术" in result
            assert result["技术"] == {"低碳": ["碳减排"]}
        finally:
            Path(temp_path).unlink()


class TestCountKeywordsV2:
    """Test count_keywords_v2 function"""

    def test_count_keywords_v2_basic(self):
        """Test basic keyword counting"""
        text = "碳减排和节能降碳是重要的碳减排技术"
        math_label_keywords = {
            "低碳": ["碳减排", "节能降碳"],
            "电动": ["电动车"]
        }

        result = count_keywords_v2(text, math_label_keywords, normalize=False)

        assert result["低碳"] == 3  # "碳减排" appears twice, "节能降碳" appears once
        assert result["电动"] == 0  # "电动车" doesn't appear

    def test_count_keywords_v2_with_normalize(self):
        """Test keyword counting with normalization"""
        text = "碳减排和节能降碳是重要的碳减排技术"  # 17 characters
        math_label_keywords = {
            "低碳": ["碳减排", "节能降碳"]
        }

        result = count_keywords_v2(text, math_label_keywords, normalize=True)

        assert result["低碳"] == 3  # 碳减排 2次, 节能降碳 1次
        assert "低碳_每万字" in result
        # 3 occurrences / (17 / 10000) = 1764.7059
        assert result["低碳_每万字"] == 1764.7059

    def test_count_keywords_v2_empty_text(self):
        """Test with empty text"""
        text = ""
        math_label_keywords = {"低碳": ["碳减排"]}

        result = count_keywords_v2(text, math_label_keywords, normalize=True)

        assert result["低碳"] == 0
        # _每万字 not added when word_count is 0 (division by zero protection)
        assert "低碳_每万字" not in result

    def test_count_keywords_v2_no_matches(self):
        """Test when no keywords match"""
        text = "这是一些无关文本"
        math_label_keywords = {"低碳": ["碳减排"], "电动": ["电动车"]}

        result = count_keywords_v2(text, math_label_keywords, normalize=False)

        assert result["低碳"] == 0
        assert result["电动"] == 0

    def test_count_keywords_v2_multiple_keywords_same_label(self):
        """Test multiple keywords for same math_label"""
        text = "碳市场碳交易碳市场碳市场"
        math_label_keywords = {"碳交易": ["碳市场", "碳交易"]}

        result = count_keywords_v2(text, math_label_keywords, normalize=False)

        # "碳市场" appears 3 times, "碳交易" appears 1 time
        assert result["碳交易"] == 4