"""CooccurrenceEvaluator 测试"""
import logging
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from tcfd_extractor.config import LLMSettings
from tcfd_extractor.evaluation.evaluator import CooccurrenceEvaluator
from tcfd_extractor.evaluation.exceptions import LLMResponseParseError
from tcfd_extractor.evaluation.models import (
    CooccurrenceContext,
    TCFDValidationResult,
)


def _make_parsed_response(is_tcfd: bool = True, dimension: str = "政策", reason: str = "符合"):
    """构造 OpenAI 客户端返回的 mock parsed 对象"""
    mock_parsed = MagicMock(spec=TCFDValidationResult)
    mock_parsed.is_tcfd_related = is_tcfd
    mock_parsed.dimension = dimension
    mock_parsed.reason = reason
    return mock_parsed


class TestEvaluatorInit:
    def test_default_settings_used(self):
        with patch("tcfd_extractor.evaluation.evaluator.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            evaluator = CooccurrenceEvaluator()
            assert evaluator.settings is not None
            assert isinstance(evaluator.settings, LLMSettings)

    def test_custom_settings_injected(self):
        custom = LLMSettings(base_url="http://test:1234/v1", model_name="test-model")
        with patch("tcfd_extractor.evaluation.evaluator.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            evaluator = CooccurrenceEvaluator(settings=custom)
            assert evaluator.settings.base_url == "http://test:1234/v1"
            assert evaluator.settings.model_name == "test-model"

    def test_openai_client_constructed_with_settings(self):
        custom = LLMSettings(base_url="http://test:1234/v1", api_key="test-key")
        with patch("tcfd_extractor.evaluation.evaluator.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            CooccurrenceEvaluator(settings=custom)
            mock_openai.assert_called_once_with(base_url="http://test:1234/v1", api_key="test-key")


class TestEvaluateSuccess:
    def test_evaluate_returns_evaluation_result(self):
        ctx = CooccurrenceContext(
            keyword_a="碳交易", keyword_b="低碳",
            context="公司参与碳交易", position=100
        )

        with patch("tcfd_extractor.evaluation.evaluator.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(parsed=_make_parsed_response(True, "政策", "符合TCFD")))]
            mock_client.beta.chat.completions.parse.return_value = mock_response
            mock_openai.return_value = mock_client

            evaluator = CooccurrenceEvaluator()
            result = evaluator.evaluate(ctx)

            assert result.is_tcfd_related is True
            assert result.dimension == "政策"
            assert result.reason == "符合TCFD"
            assert result.keyword_a == "碳交易"
            assert result.keyword_b == "低碳"

    def test_evaluate_empty_context_does_not_raise(self):
        """空 context 也应正常调用 LLM,不应在客户端层抛异常"""
        ctx = CooccurrenceContext(
            keyword_a="a", keyword_b="b", context="", position=0
        )
        with patch("tcfd_extractor.evaluation.evaluator.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(parsed=_make_parsed_response(False, "无", "空内容")))]
            mock_client.beta.chat.completions.parse.return_value = mock_response
            mock_openai.return_value = mock_client

            evaluator = CooccurrenceEvaluator()
            result = evaluator.evaluate(ctx)
            assert result.is_tcfd_related is False


class TestEvaluateParseError:
    """畸形 JSON 响应防御测试(DoD 关键项)"""

    def test_parse_error_raises_llm_response_parse_error(self, caplog):
        """LLM 返回畸形 JSON 时,抛 LLMResponseParseError"""
        ctx = CooccurrenceContext(
            keyword_a="a", keyword_b="b", context="c", position=0
        )
        malformed_json = '{"is_tcfd_related": tru, "reason": invalid}'

        with patch("tcfd_extractor.evaluation.evaluator.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(
                parsed=None,
                content=malformed_json
            ))]
            mock_client.beta.chat.completions.parse.return_value = mock_response
            mock_openai.return_value = mock_client

            evaluator = CooccurrenceEvaluator()
            with caplog.at_level(logging.ERROR):
                with pytest.raises(LLMResponseParseError):
                    evaluator.evaluate(ctx)

            # 验证原始响应文本被记录(关键可观测性)
            assert any(malformed_json in record.message for record in caplog.records), \
                "原始畸形 JSON 响应必须被记录到日志"

    def test_validation_error_raises_llm_response_parse_error(self, caplog):
        """LLM 返回 JSON 但字段不匹配 Pydantic 模型时抛 LLMResponseParseError"""
        ctx = CooccurrenceContext(
            keyword_a="a", keyword_b="b", context="c", position=0
        )

        with patch("tcfd_extractor.evaluation.evaluator.OpenAI") as mock_openai:
            mock_client = MagicMock()
            # mock parse() 抛 ValidationError
            mock_client.beta.chat.completions.parse.side_effect = ValidationError.from_exception_data(
                title="TCFDValidationResult",
                line_errors=[{"type": "missing", "loc": ("is_tcfd_related",), "input": {}, "ctx": {}}]
            )
            mock_openai.return_value = mock_client

            evaluator = CooccurrenceEvaluator()
            with caplog.at_level(logging.ERROR):
                with pytest.raises(LLMResponseParseError):
                    evaluator.evaluate(ctx)