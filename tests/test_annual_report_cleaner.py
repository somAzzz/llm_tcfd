import pytest
import tempfile
from pathlib import Path
from src.utils.annual_report_cleaner import AnnualReportCleaner

def test_find_financial_section():
    """测试找到财务章节位置"""
    content = "第一章 经营情况\n九、财务会计报告\n附件：财务报表"
    result = AnnualReportCleaner._find_financial_section(content)
    assert result is not None
    assert content[result["position"]] == "九"

def test_trim_content():
    """测试截断内容"""
    content = "第一章 经营情况\n九、财务会计报告\n附件：报表"
    result = AnnualReportCleaner._trim_after_section(content, 15)
    assert "九、财务会计报告" not in result
    assert "第一章 经营情况" in result

def test_word_count_ratio():
    """测试字数比例计算"""
    original = "第一章正文内容" + "x" * 100
    trimmed = "第一章正文内容"
    ratio = AnnualReportCleaner._calc_keep_ratio(original, trimmed)
    assert ratio < 0.5

def test_problem_file_detection():
    """测试问题文件判定（保留<50%为问题）"""
    original = "x" * 10000
    trimmed = "x" * 4000  # 40%
    assert AnnualReportCleaner._is_problem_file(original, trimmed) is True

def test_clean_single_with_file():
    """测试 clean_single 对真实文件的处理"""
    # Use enough content so keep_ratio > 0.5 (not a problem file)
    content = "第一章 经营情况概述" + "x" * 10000 + "\n九、财务会计报告\n附件：财务报表"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = Path(f.name)

    try:
        result = AnnualReportCleaner.clean_single(temp_path)
        assert result.status == "ok"
        assert result.original_chars == len(content)
        assert result.kept_chars < result.original_chars
        assert "九、财务会计报告" not in temp_path.read_text(encoding='utf-8')[:result.kept_chars]
    finally:
        temp_path.unlink()

def test_clean_single_not_found():
    """测试 clean_single 未找到财务章节的情况"""
    content = "第一章 经营情况\n这里没有财务章节"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = Path(f.name)

    try:
        result = AnnualReportCleaner.clean_single(temp_path)
        assert result.status == "not_found"
        assert result.kept_chars == result.original_chars
        assert result.keep_ratio == 1.0
    finally:
        temp_path.unlink()