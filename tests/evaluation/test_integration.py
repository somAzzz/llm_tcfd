"""评估模块端到端集成测试

验证 parser → batch → summary 完整流水线,
所有 LLM 调用通过 mock 拦截。
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tcfd_extractor.config import BatchSettings, LLMSettings
from tcfd_extractor.evaluation.batch import BatchEvaluator
from tcfd_extractor.evaluation.evaluator import CooccurrenceEvaluator
from tcfd_extractor.evaluation.models import EvaluationResult
from tcfd_extractor.evaluation.summary import (
    compute_statistics,
    generate_summary,
)


def _write_md(tmp_path: Path, content: str, name: str) -> Path:
    md = tmp_path / name
    md.write_text(content, encoding="utf-8")
    return md


class TestEndToEnd:
    """端到端: parser → batch → summary"""

    def test_full_pipeline(self, tmp_path):
        """完整流水线: 解析 MD → 并发评估 → 计算统计 → 生成总结"""
        # 准备输入
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        _write_md(input_dir, """# 测试公司A - 2020年度报告

**碳交易** + **低碳** (2次共现)
1. "...公司参与碳交易..." (位置: 100)
2. "...推进低碳转型..." (位置: 200)
""", name="a.md")
        _write_md(input_dir, """# 测试公司B - 2020年度报告

**可持续发展** + **环保** (1次共现)
1. "...坚持可持续发展..." (位置: 300)
""", name="b.md")
        results_file = tmp_path / "results.jsonl"
        summary_file = tmp_path / "summary.md"

        # Mock LLM 客户端(所有评估返回 True)
        with patch("tcfd_extractor.evaluation.evaluator.OpenAI") as mock_openai, \
             patch("tcfd_extractor.evaluation.summary.OpenAI") as mock_summary_openai:
            mock_parsed = MagicMock()
            mock_parsed.is_tcfd_related = True
            mock_parsed.dimension = "政策"
            mock_parsed.reason = "符合"

            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(
                parsed=mock_parsed, content='# 总结\n\n准确率: 100.0%\n\n评估统计: 100 个片段, 100 个 TCFD 相关。'
            ))]
            mock_client = MagicMock()
            mock_client.beta.chat.completions.parse.return_value = mock_response
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            mock_summary_openai.return_value = mock_client

            # 流水线
            settings = LLMSettings()
            batch_settings = BatchSettings(workers=2, max_retries=1)
            evaluator = CooccurrenceEvaluator(settings=settings)
            batch = BatchEvaluator(evaluator, settings=batch_settings)
            stats = batch.evaluate_all(input_dir, results_file)

            assert stats["total"] == 3  # 2+1 contexts
            assert stats["tcfd_count"] == 3
            assert results_file.exists()

            # compute_statistics
            statistics = compute_statistics(results_file)
            assert statistics["total"] == 3
            assert statistics["tcfd_count"] == 3
            assert statistics["policy_count"] == 3
            assert statistics["accuracy"] == 100.0

            # generate_summary(mock LLM 已就绪,验证调用)
            generate_summary(statistics, summary_file, settings=settings)
            assert summary_file.exists()
            content = summary_file.read_text(encoding="utf-8")
            assert "100.0" in content or "100" in content

    def test_pipeline_with_parse_errors(self, tmp_path):
        """流水线处理部分解析错误,其他文件继续评估"""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        # 1 个有效文件 + 1 个无效文件
        _write_md(input_dir, """# 测试公司A - 2020年度报告

**碳交易** + **低碳** (1次共现)
1. "...公司参与碳交易..." (位置: 100)
""", name="valid.md")
        _write_md(input_dir, "# 无效格式\n", name="invalid.md")
        results_file = tmp_path / "results.jsonl"

        with patch("tcfd_extractor.evaluation.evaluator.OpenAI") as mock_openai:
            mock_parsed = MagicMock()
            mock_parsed.is_tcfd_related = True
            mock_parsed.dimension = "政策"
            mock_parsed.reason = "符合"
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(
                parsed=mock_parsed, content=''
            ))]
            mock_client = MagicMock()
            mock_client.beta.chat.completions.parse.return_value = mock_response
            mock_openai.return_value = mock_client

            settings = LLMSettings()
            batch = BatchEvaluator(
                CooccurrenceEvaluator(settings=settings),
                settings=BatchSettings(workers=1, max_retries=0),
            )
            stats = batch.evaluate_all(input_dir, results_file)

            # 1 个有效文件被处理,1 个解析失败
            assert stats["total"] == 1
            assert stats["parse_errors"] == 1
            assert stats["tcfd_count"] == 1


class TestBackwardCompatibility:
    """向后兼容: 旧 import 路径仍可用"""

    def test_old_imports_still_work(self):
        """通过 cooccurrence_evaluator 薄壳的 import 仍可用"""
        from tcfd_extractor.evaluation.cooccurrence_evaluator import (
            CooccurrenceContext,
            TCFDValidationResult,
            EvaluationResult,
            FileParseResult,
            parse_cooccurrence_md,
            CooccurrenceEvaluator,
            BatchEvaluator,
            generate_summary,
            EVAL_SYSTEM_PROMPT,
            EVAL_USER_PROMPT,
            SUMMARY_SYSTEM_PROMPT,
            SUMMARY_USER_PROMPT,
        )
        # 验证都是真实可用的对象
        assert CooccurrenceContext.__name__ == "CooccurrenceContext"
        assert parse_cooccurrence_md.__name__ == "parse_cooccurrence_md"
        assert CooccurrenceEvaluator.__name__ == "CooccurrenceEvaluator"