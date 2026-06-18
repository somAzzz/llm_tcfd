"""自定义异常层次测试"""
import pytest

from tcfd_extractor.evaluation.exceptions import (
    EvaluationError,
    LLMEvaluationError,
    LLMUnavailableError,
    LLMResponseParseError,
    LLMTimeoutError,
)


class TestExceptionHierarchy:
    def test_evaluation_error_is_exception(self):
        assert issubclass(EvaluationError, Exception)

    def test_llm_evaluation_error_inherits_evaluation_error(self):
        assert issubclass(LLMEvaluationError, EvaluationError)

    def test_llm_unavailable_inherits_llm_evaluation_error(self):
        assert issubclass(LLMUnavailableError, LLMEvaluationError)

    def test_llm_response_parse_inherits_llm_evaluation_error(self):
        assert issubclass(LLMResponseParseError, LLMEvaluationError)

    def test_llm_timeout_inherits_llm_evaluation_error(self):
        assert issubclass(LLMTimeoutError, LLMEvaluationError)

    def test_can_raise_and_catch(self):
        with pytest.raises(LLMUnavailableError) as excinfo:
            raise LLMUnavailableError("API 不可达")
        assert "API 不可达" in str(excinfo.value)

    def test_can_catch_via_base_class(self):
        with pytest.raises(LLMEvaluationError):
            raise LLMResponseParseError("畸形 JSON")
