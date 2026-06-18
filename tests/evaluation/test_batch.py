"""BatchEvaluator 测试"""
import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tcfd_extractor.config import BatchSettings
from tcfd_extractor.evaluation.batch import BatchEvaluator
from tcfd_extractor.evaluation.exceptions import LLMUnavailableError
from tcfd_extractor.evaluation.models import (
    CooccurrenceContext,
    EvaluationResult,
)


def _make_eval_result(keyword_a="a", keyword_b="b", is_tcfd=True, reason="符合"):
    return EvaluationResult(
        keyword_a=keyword_a, keyword_b=keyword_b,
        context="c", position=0,
        is_tcfd_related=is_tcfd, dimension="政策" if is_tcfd else "无",
        reason=reason
    )


def _write_md(tmp_path: Path, content: str, name: str = "test.md") -> Path:
    md = tmp_path / name
    md.write_text(content, encoding="utf-8")
    return md


class TestBatchInit:
    def test_default_settings(self):
        mock_evaluator = MagicMock()
        batch = BatchEvaluator(mock_evaluator)
        assert isinstance(batch.settings, BatchSettings)
        assert batch.evaluator is mock_evaluator

    def test_custom_settings(self):
        mock_evaluator = MagicMock()
        custom = BatchSettings(workers=2, max_retries=1, retry_delay=0.1)
        batch = BatchEvaluator(mock_evaluator, settings=custom)
        assert batch.settings.workers == 2
        assert batch.settings.max_retries == 1


class TestBatchEvaluateAll:
    def test_evaluate_all_writes_jsonl(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        _write_md(input_dir, """# 测试公司 - 2020年度报告

**碳交易** + **低碳** (1次共现)
1. "...公司参与碳交易..." (位置: 100)
""")
        output_file = tmp_path / "output.jsonl"

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = _make_eval_result()
        batch = BatchEvaluator(mock_evaluator, settings=BatchSettings(workers=1))
        stats = batch.evaluate_all(input_dir, output_file)

        assert stats["total"] == 1
        assert stats["tcfd_count"] == 1
        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "碳交易" in content
        assert "低碳" in content
        assert "true" in content.lower() or "符合" in content

    def test_evaluate_all_parse_error_skipped(self, tmp_path):
        """文件解析失败时,不应影响其他文件"""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        # 第一个文件:无效格式
        _write_md(input_dir, "# 无效格式\n", name="bad.md")
        # 第二个文件:有效
        _write_md(input_dir, """# 测试公司 - 2020年度报告

**碳交易** + **低碳** (1次共现)
1. "...公司参与碳交易..." (位置: 100)
""", name="good.md")
        output_file = tmp_path / "output.jsonl"

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = _make_eval_result()
        batch = BatchEvaluator(mock_evaluator, settings=BatchSettings(workers=1))
        stats = batch.evaluate_all(input_dir, output_file)

        # 有效文件应被解析,无效文件应被跳过
        assert stats["total"] == 1
        assert stats["parse_errors"] == 1

    def test_evaluate_all_max_retries_zero_raises(self, tmp_path):
        """max_retries=0 时,LLM 失败立即抛 LLMUnavailableError(spec §3.5)"""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        _write_md(input_dir, """# 测试公司 - 2020年度报告

**碳交易** + **低碳** (1次共现)
1. "...公司参与碳交易..." (位置: 100)
""")
        output_file = tmp_path / "output.jsonl"

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.side_effect = RuntimeError("LLM 失败")
        batch = BatchEvaluator(
            mock_evaluator,
            settings=BatchSettings(workers=1, max_retries=0)
        )
        with pytest.raises(LLMUnavailableError) as excinfo:
            batch.evaluate_all(input_dir, output_file)
        # 验证错误信息包含原始异常
        assert "LLM 失败" in str(excinfo.value) or "RuntimeError" in str(excinfo.value)

    def test_evaluate_all_uses_generators_for_memory_safety(self, tmp_path):
        """验证 _parse_all_files 是生成器(惰性加载)"""
        from tcfd_extractor.evaluation.batch import BatchEvaluator as BE
        # 关键: 验证私有方法用 yield 而非 return list
        import inspect
        source = inspect.getsource(BE._parse_all_files)
        assert "yield" in source, "_parse_all_files 必须是生成器(用 yield)"
        assert "return" not in source.replace("return company", "").replace("return year", ""), \
            "_parse_all_files 不应返回 list"

    def test_evaluate_all_concurrent_execution(self, tmp_path):
        """workers > 1 时并发执行"""
        import time
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        # 4 个 context
        for i in range(4):
            _write_md(input_dir, f"""# 测试公司 - 2020年度报告

**碳交易** + **低碳** ({i+1}次共现)
1. "...公司参与碳交易 {i}..." (位置: {i*100})
""", name=f"f{i}.md")
        output_file = tmp_path / "output.jsonl"

        def slow_evaluate(ctx):
            time.sleep(0.05)
            return _make_eval_result()

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.side_effect = slow_evaluate
        batch = BatchEvaluator(
            mock_evaluator,
            settings=BatchSettings(workers=4, max_retries=1)
        )
        start = time.time()
        stats = batch.evaluate_all(input_dir, output_file)
        elapsed = time.time() - start

        # 4 个 × 50ms 串行需 200ms,4 并发应 < 150ms
        assert stats["total"] == 4
        assert elapsed < 0.15, f"并发执行应 < 150ms,实际 {elapsed*1000:.0f}ms"

    def test_unrecoverable_failure_raises_llm_unavailable(self, tmp_path):
        """spec §3.5 DoD: LLM 连续失败 max_retries 次后,抛 LLMUnavailableError 终止批处理"""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        _write_md(input_dir, """# 测试公司 - 2020年度报告

**碳交易** + **低碳** (1次共现)
1. "...公司参与碳交易..." (位置: 100)
""")
        output_file = tmp_path / "output.jsonl"

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.side_effect = RuntimeError("LLM 不可达")

        batch = BatchEvaluator(
            mock_evaluator,
            settings=BatchSettings(workers=1, max_retries=2)
        )
        with pytest.raises(LLMUnavailableError) as excinfo:
            batch.evaluate_all(input_dir, output_file)
        # 验证错误信息包含关键词和原始异常
        assert "LLM 不可达" in str(excinfo.value)
        assert "连续失败" in str(excinfo.value)
        # 验证异常链保留原始异常
        assert isinstance(excinfo.value.__cause__, RuntimeError)
