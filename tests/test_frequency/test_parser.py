import pytest
from pathlib import Path
from tcfd_extractor.frequency.parser import parse_filename


def test_parse_filename_with_dash():
    """测试用-分隔的文件名"""
    result = parse_filename("000001-平安银行-2023年年度报告.txt")
    assert result == {
        "company_id": "000001",
        "company_name": "平安银行",
        "year": 2023
    }


def test_parse_filename_with_underscore():
    """测试用_分隔的文件名"""
    result = parse_filename("000001_平安银行_2023年年度报告.txt")
    assert result == {
        "company_id": "000001",
        "company_name": "平安银行",
        "year": 2023
    }
