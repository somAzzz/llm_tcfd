# tests/test_cooccurrence_evaluator.py
"""共现评估器测试"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tcfd_extractor.evaluation.cooccurrence_evaluator import (
    CooccurrenceContext,
    EvaluationResult,
    FileParseResult,
    parse_cooccurrence_md,
    CooccurrenceEvaluator,
    BatchEvaluator,
    generate_summary,
)


class TestCooccurrenceContext:
    """CooccurrenceContext数据模型测试"""

    def test_create_context(self):
        """测试创建共现上下文"""
        ctx = CooccurrenceContext(
            keyword_a="碳交易",
            keyword_b="低碳",
            context="公司积极参与碳交易，推进低碳转型",
            position=1234,
            count=2
        )
        assert ctx.keyword_a == "碳交易"
        assert ctx.keyword_b == "低碳"
        assert ctx.count == 2
        assert ctx.position == 1234

    def test_default_count(self):
        """测试默认共现次数为1"""
        ctx = CooccurrenceContext(
            keyword_a="碳交易",
            keyword_b="低碳",
            context="公司积极参与碳交易",
            position=1234
        )
        assert ctx.count == 1


class TestEvaluationResult:
    """EvaluationResult数据模型测试"""

    def test_create_result(self):
        """测试创建评估结果"""
        result = EvaluationResult(
            keyword_a="碳交易",
            keyword_b="低碳",
            context="公司积极参与碳交易",
            position=1234,
            is_tcfd_related=True,
            reason="符合TCFD标准"
        )
        assert result.is_tcfd_related is True
        assert result.reason == "符合TCFD标准"

    def test_reason_max_length(self):
        """测试reason字段最大长度限制"""
        result = EvaluationResult(
            keyword_a="碳交易",
            keyword_b="低碳",
            context="公司积极参与碳交易",
            position=1234,
            is_tcfd_related=False,
            reason="A" * 50  # 50 chars - at limit
        )
        assert len(result.reason) == 50


class TestFileParseResult:
    """FileParseResult数据模型测试"""

    def test_create_parse_result(self):
        """测试创建解析结果"""
        contexts = [
            CooccurrenceContext(
                keyword_a="碳交易",
                keyword_b="低碳",
                context="上下文1",
                position=100,
                count=1
            )
        ]
        result = FileParseResult(
            file="test.md",
            company="测试公司",
            year=2020,
            contexts=contexts
        )
        assert result.company == "测试公司"
        assert result.year == 2020
        assert len(result.contexts) == 1


class TestParseCooccurrenceMd:
    """Markdown解析器测试"""

    def test_parse_simple_file(self, tmp_path):
        """测试解析简单格式的MD文件"""
        content = """# 测试公司 - 2020年度报告

## 共现上下文汇总

### 碳交易

**碳交易** + **低碳** (2次共现)
1. "...公司积极参与碳交易，推进低碳转型..." (位置: 100)
2. "...碳交易市场规模扩大，低碳成为趋势..." (位置: 200)

---

### 环保

**可持续发展** + **环保** (1次共现)
1. "...公司坚持可持续发展理念，注重环保..." (位置: 300)

---
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        result = parse_cooccurrence_md(md_file)

        assert result.company == "测试公司"
        assert result.year == 2020
        assert len(result.contexts) == 3

        # 验证第一个共现对
        ctx1 = result.contexts[0]
        assert ctx1.keyword_a == "碳交易"
        assert ctx1.keyword_b == "低碳"
        assert ctx1.context == "公司积极参与碳交易，推进低碳转型"
        assert ctx1.position == 100
        assert ctx1.count == 2

        # 验证第三个上下文
        ctx3 = result.contexts[2]
        assert ctx3.keyword_a == "可持续发展"
        assert ctx3.keyword_b == "环保"
        assert ctx3.position == 300

    def test_parse_without_report_suffix(self, tmp_path):
        """测试解析没有"年度"后缀的报告"""
        content = """# 测试公司 - 2020报告

## 共现上下文汇总

### 碳交易

**碳交易** + **低碳** (1次共现)
1. "...公司积极参与碳交易..." (位置: 100)

---
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        result = parse_cooccurrence_md(md_file)
        assert result.company == "测试公司"
        assert result.year == 2020

    def test_parse_invalid_header(self, tmp_path):
        """测试解析无效文件头"""
        content = """# 无效格式

内容...
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        with pytest.raises(ValueError, match="无法解析文件头"):
            parse_cooccurrence_md(md_file)

    def test_parse_empty_file(self, tmp_path):
        """测试解析空文件"""
        md_file = tmp_path / "empty.md"
        md_file.write_text("", encoding="utf-8")

        with pytest.raises(ValueError, match="无法解析文件头"):
            parse_cooccurrence_md(md_file)

    def test_parse_real_file(self):
        """测试解析真实文件"""
        # 使用项目中存在的文件
        real_file = Path("/home/bo/projects/python/frequency_analyzer/output/sample_100/cooccurrence_context/600377-宁沪高速-2020年年度报告.md")
        if real_file.exists():
            result = parse_cooccurrence_md(real_file)
            assert result.company == "宁沪高速"
            assert result.year == 2020
            assert len(result.contexts) >= 0


class TestCooccurrenceEvaluator:
    """LLM评估器测试"""

    def test_evaluate_success(self):
        """测试成功评估"""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"is_tcfd_related": true, "reason": "符合TCFD标准"}'))
        ]

        with patch("tcfd_extractor.evaluation.cooccurrence_evaluator.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            evaluator = CooccurrenceEvaluator()
            ctx = CooccurrenceContext(
                keyword_a="碳交易",
                keyword_b="低碳",
                context="公司参与碳交易",
                position=100
            )

            result = evaluator.evaluate(ctx)

            assert result.is_tcfd_related is True
            assert result.reason == "符合TCFD标准"
            assert result.keyword_a == "碳交易"

    def test_evaluate_with_markdown_code_block(self):
        """测试解析带markdown代码块的响应"""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='```json\n{"is_tcfd_related": false, "reason": "不相关"}\n```'))
        ]

        with patch("tcfd_extractor.evaluation.cooccurrence_evaluator.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            evaluator = CooccurrenceEvaluator()
            ctx = CooccurrenceContext(
                keyword_a="手机",
                keyword_b="短信",
                context="手机发送短信",
                position=100
            )

            result = evaluator.evaluate(ctx)

            assert result.is_tcfd_related is False
            assert result.reason == "不相关"


class TestBatchEvaluator:
    """批量评估器测试"""

    def test_evaluate_all_with_mock(self, tmp_path):
        """测试批量评估（使用mock）"""
        # 创建测试MD文件
        md_content = """# 测试公司 - 2020年度报告

## 共现上下文汇总

### 碳交易

**碳交易** + **低碳** (1次共现)
1. "...公司参与碳交易..." (位置: 100)

---
"""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        md_file = input_dir / "test.md"
        md_file.write_text(md_content, encoding="utf-8")

        output_file = tmp_path / "output.jsonl"

        # Mock评估器
        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = EvaluationResult(
            keyword_a="碳交易",
            keyword_b="低碳",
            context="公司参与碳交易",
            position=100,
            is_tcfd_related=True,
            reason="符合TCFD"
        )

        batch_evaluator = BatchEvaluator(mock_evaluator)
        stats = batch_evaluator.evaluate_all(input_dir, output_file)

        assert stats["total"] == 1
        assert stats["tcfd_count"] == 1
        assert output_file.exists()

    def test_evaluate_all_parse_error(self, tmp_path):
        """测试批量评估时解析错误处理"""
        # 创建无效MD文件
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        md_file = input_dir / "invalid.md"
        md_file.write_text("# 无效格式", encoding="utf-8")

        output_file = tmp_path / "output.jsonl"

        mock_evaluator = MagicMock()
        batch_evaluator = BatchEvaluator(mock_evaluator)
        stats = batch_evaluator.evaluate_all(input_dir, output_file)

        # 解析失败，不应产生任何结果
        assert stats["total"] == 0
        assert stats["tcfd_count"] == 0


class TestGenerateSummary:
    """总结生成器测试"""

    def test_generate_summary_with_results(self, tmp_path):
        """测试生成总结（有时间）"""
        results_file = tmp_path / "results.jsonl"
        summary_file = tmp_path / "summary.md"

        # 创建测试结果
        with open(results_file, "w", encoding="utf-8") as f:
            f.write('{"keyword_a": "碳交易", "keyword_b": "低碳", "is_tcfd_related": true, "reason": "符合"}\n')
            f.write('{"keyword_a": "手机", "keyword_b": "短信", "is_tcfd_related": false, "reason": "不相关"}\n')

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="# 总结报告\n\n准确率: 50%"))
        ]

        with patch("tcfd_extractor.evaluation.cooccurrence_evaluator.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            stats = generate_summary(results_file, summary_file)

            assert stats["total"] == 2
            assert stats["tcfd_count"] == 1
            assert stats["accuracy"] == 50.0
            assert summary_file.exists()

    def test_generate_summary_empty_results(self, tmp_path):
        """测试空结果文件"""
        results_file = tmp_path / "empty.jsonl"
        results_file.write_text("", encoding="utf-8")

        summary_file = tmp_path / "summary.md"

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="# 总结报告\n\n无数据"))
        ]

        with patch("tcfd_extractor.evaluation.cooccurrence_evaluator.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            stats = generate_summary(results_file, summary_file)

            assert stats["total"] == 0
            assert stats["accuracy"] == 0.0
