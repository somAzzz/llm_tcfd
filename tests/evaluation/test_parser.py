"""Markdown 解析器测试"""
import pytest
from pathlib import Path

from tcfd_extractor.evaluation.parser import parse_cooccurrence_md
from tcfd_extractor.evaluation.models import CooccurrenceContext, FileParseResult


class TestParseSimpleFile:
    """简单格式 MD 文件解析测试"""

    def _write_md(self, tmp_path: Path, content: str) -> Path:
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")
        return md_file

    def test_parse_simple_file(self, tmp_path):
        content = """# 测试公司 - 2020年度报告

## 共现上下文汇总

### 碳交易

**碳交易** + **低碳** (2次共现)
1. "...公司积极参与碳交易,推进低碳转型..." (位置: 100)
2. "...碳交易市场规模扩大,低碳成为趋势..." (位置: 200)

---

### 环保

**可持续发展** + **环保** (1次共现)
1. "...公司坚持可持续发展理念,注重环保..." (位置: 300)

---
"""
        md_file = self._write_md(tmp_path, content)
        result = parse_cooccurrence_md(md_file)

        assert isinstance(result, FileParseResult)
        assert result.company == "测试公司"
        assert result.year == 2020
        assert len(result.contexts) == 3

        ctx1 = result.contexts[0]
        assert ctx1.keyword_a == "碳交易"
        assert ctx1.keyword_b == "低碳"
        assert ctx1.context == "公司积极参与碳交易,推进低碳转型"
        assert ctx1.position == 100
        assert ctx1.count == 2

    def test_parse_without_report_suffix(self, tmp_path):
        content = """# 测试公司 - 2020报告

**碳交易** + **低碳** (1次共现)
1. "...公司积极参与碳交易..." (位置: 100)
"""
        md_file = self._write_md(tmp_path, content)
        result = parse_cooccurrence_md(md_file)
        assert result.company == "测试公司"
        assert result.year == 2020


class TestParseEdgeCases:
    """边界情况测试"""

    def test_parse_invalid_header_falls_back(self, tmp_path):
        content = """# 无效格式

内容...
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        result = parse_cooccurrence_md(md_file)
        assert result.company == "test"
        assert result.year == 0
        assert result.contexts == []

    def test_parse_empty_file_falls_back(self, tmp_path):
        md_file = tmp_path / "empty.md"
        md_file.write_text("", encoding="utf-8")

        result = parse_cooccurrence_md(md_file)
        assert result.company == "empty"
        assert result.year == 0
        assert result.contexts == []

    def test_parse_file_with_no_contexts(self, tmp_path):
        """有效文件头但无共现对 - 应该正常返回空 contexts"""
        content = """# 测试公司 - 2020年度报告

## 共现上下文汇总

无共现数据
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")
        result = parse_cooccurrence_md(md_file)
        assert result.company == "测试公司"
        assert result.year == 2020
        assert result.contexts == []

    def test_parse_fallback_to_path_year(self, tmp_path):
        """无效文件头时,fallback 到路径中的年份"""
        # 创建路径中含 4 位数年份的目录
        year_dir = tmp_path / "2023"
        year_dir.mkdir()
        md_file = year_dir / "company.md"
        # 文件名是 stem (不含 .md)
        md_file.write_text("# 无效格式\n", encoding="utf-8")
        # 路径含 2023,但文件头无效
        result = parse_cooccurrence_md(md_file)
        assert result.year == 2023
        assert result.company == "company"

    def test_parse_fallback_to_filename_when_no_year_in_path(self, tmp_path):
        """文件头无效且路径无年份 - fallback 到文件名"""
        md_file = tmp_path / "mycompany.md"
        md_file.write_text("# 无效格式\n", encoding="utf-8")
        result = parse_cooccurrence_md(md_file)
        assert result.company == "mycompany"
        assert result.year == 0


class TestParseMultiplePairs:
    """多共现对文件测试"""

    def test_parse_three_pairs(self, tmp_path):
        content = """# 测试公司 - 2020年度报告

**碳交易** + **低碳** (1次共现)
1. "...公司参与碳交易..." (位置: 100)

**可持续发展** + **环保** (2次共现)
1. "...坚持可持续发展..." (位置: 200)
2. "...注重环保..." (位置: 300)

**绿色金融** + **碳排放** (1次共现)
1. "...绿色金融支持碳排放..." (位置: 400)
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")
        result = parse_cooccurrence_md(md_file)

        assert len(result.contexts) == 4
        # 验证每对正确归类
        assert result.contexts[0].keyword_a == "碳交易"
        assert result.contexts[1].keyword_a == "可持续发展"
        assert result.contexts[2].keyword_a == "可持续发展"
        assert result.contexts[3].keyword_a == "绿色金融"

    def test_parse_chinese_punctuation_context(self, tmp_path):
        """含中文全角标点(，。；)的上下文应被正确保留在 capture group 中"""
        content = """# 测试公司 - 2020年度报告

**碳交易** + **低碳** (1次共现)
1. "...公司参与碳交易，推进低碳转型；实现绿色发展。..." (位置: 100)
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")
        result = parse_cooccurrence_md(md_file)

        assert len(result.contexts) == 1
        # 验证全角标点被原样保留
        assert "，" in result.contexts[0].context  # 验证全角逗号被保留
        assert "；" in result.contexts[0].context  # 验证全角分号被保留
        assert "。" in result.contexts[0].context  # 验证全角句号被保留
        # 验证 context 内容
        assert "公司参与碳交易" in result.contexts[0].context
        assert "推进低碳转型" in result.contexts[0].context

    def test_parse_with_dash_separator(self, tmp_path):
        """`---` 分隔符不应破坏解析"""
        content = """# 测试公司 - 2020年度报告

**碳交易** + **低碳** (1次共现)
1. "...公司参与碳交易..." (位置: 100)

---

**可持续发展** + **环保** (1次共现)
1. "...坚持可持续发展..." (位置: 200)
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")
        result = parse_cooccurrence_md(md_file)

        assert len(result.contexts) == 2
        assert result.contexts[0].keyword_a == "碳交易"
        assert result.contexts[1].keyword_a == "可持续发展"