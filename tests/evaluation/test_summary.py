"""summary 模块测试"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tcfd_extractor.config import LLMSettings
from tcfd_extractor.evaluation.exceptions import LLMEvaluationError
from tcfd_extractor.evaluation.summary import compute_statistics, generate_summary


def _write_jsonl(tmp_path: Path, records: list[dict]) -> Path:
    f = tmp_path / "results.jsonl"
    with open(f, "w", encoding="utf-8") as fp:
        for r in records:
            fp.write(json.dumps(r, ensure_ascii=False) + "\n")
    return f


class TestComputeStatistics:
    def test_empty_file(self, tmp_path):
        f = _write_jsonl(tmp_path, [])
        stats = compute_statistics(f)
        assert stats["total"] == 0
        assert stats["tcfd_count"] == 0
        assert stats["accuracy"] == 0.0

    def test_basic_counting(self, tmp_path):
        f = _write_jsonl(tmp_path, [
            {"is_tcfd_related": True, "dimension": "政策"},
            {"is_tcfd_related": True, "dimension": "市场"},
            {"is_tcfd_related": False, "dimension": "无"},
        ])
        stats = compute_statistics(f)
        assert stats["total"] == 3
        assert stats["tcfd_count"] == 2
        assert stats["policy_count"] == 1
        assert stats["market_count"] == 1
        assert stats["tech_count"] == 0
        # accuracy = 2/3 * 100 = 66.67
        assert 66.0 < stats["accuracy"] < 67.0

    def test_dimension_counts(self, tmp_path):
        f = _write_jsonl(tmp_path, [
            {"is_tcfd_related": True, "dimension": "政策"},
            {"is_tcfd_related": True, "dimension": "政策"},
            {"is_tcfd_related": True, "dimension": "市场"},
            {"is_tcfd_related": True, "dimension": "技术"},
            {"is_tcfd_related": True, "dimension": "技术"},
            {"is_tcfd_related": True, "dimension": "技术"},
        ])
        stats = compute_statistics(f)
        assert stats["policy_count"] == 2
        assert stats["market_count"] == 1
        assert stats["tech_count"] == 3

    def test_corrupted_line_skipped(self, tmp_path):
        f = tmp_path / "results.jsonl"
        f.write_text(
            '{"is_tcfd_related": true, "dimension": "政策"}\n'
            'NOT VALID JSON\n'
            '{"is_tcfd_related": false, "dimension": "无"}\n',
            encoding="utf-8"
        )
        stats = compute_statistics(f)
        # 损坏行被跳过,只统计 2 条
        assert stats["total"] == 2

    def test_missing_dimension_defaults_to_wu(self, tmp_path):
        f = _write_jsonl(tmp_path, [
            {"is_tcfd_related": True},  # 无 dimension 字段
        ])
        stats = compute_statistics(f)
        assert stats["total"] == 1
        assert stats["tcfd_count"] == 1
        # 没有 dimension 字段,不计入任何具体维度
        assert stats["policy_count"] == 0
        assert stats["market_count"] == 0
        assert stats["tech_count"] == 0


class TestGenerateSummary:
    def test_generate_summary_uses_precomputed_stats(self, tmp_path):
        """generate_summary 接受预先计算好的 stats,不读 JSONL"""
        summary_file = tmp_path / "summary.md"
        stats = {
            "total": 100, "tcfd_count": 80,
            "non_tcfd_count": 20, "accuracy": 80.0,
            "policy_count": 30, "market_count": 25, "tech_count": 25,
        }

        with patch("tcfd_extractor.evaluation.summary.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(
                content="# 总结\n\n准确率: 80%"
            ))]
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            generate_summary(stats, summary_file)
            assert summary_file.exists()
            content = summary_file.read_text(encoding="utf-8")
            assert "80%" in content

    def test_generate_summary_uses_settings(self, tmp_path):
        """generate_summary 使用传入的 settings"""
        summary_file = tmp_path / "summary.md"
        stats = {
            "total": 10, "tcfd_count": 5,
            "non_tcfd_count": 5, "accuracy": 50.0,
            "policy_count": 2, "market_count": 2, "tech_count": 1,
        }
        custom = LLMSettings(base_url="http://test:1234/v1", api_key="k", model_name="m")

        with patch("tcfd_extractor.evaluation.summary.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="ok"))]
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            generate_summary(stats, summary_file, settings=custom)
            mock_openai.assert_called_once_with(base_url="http://test:1234/v1", api_key="k")

    def test_generate_summary_llm_failure_raises(self, tmp_path):
        """LLM 失败应抛 LLMEvaluationError"""
        summary_file = tmp_path / "summary.md"
        stats = {
            "total": 10, "tcfd_count": 5,
            "non_tcfd_count": 5, "accuracy": 50.0,
            "policy_count": 0, "market_count": 0, "tech_count": 0,
        }

        with patch("tcfd_extractor.evaluation.summary.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = RuntimeError("LLM 不可用")
            mock_openai.return_value = mock_client

            with pytest.raises(LLMEvaluationError):
                generate_summary(stats, summary_file)