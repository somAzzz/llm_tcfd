"""数据模型测试"""
import pytest
from pydantic import ValidationError

from tcfd_extractor.evaluation.models import (
    CooccurrenceContext,
    TCFDValidationResult,
    EvaluationResult,
    FileParseResult,
)


class TestCooccurrenceContext:
    def test_create_context(self):
        ctx = CooccurrenceContext(
            keyword_a="碳交易", keyword_b="低碳",
            context="公司参与碳交易", position=100
        )
        assert ctx.keyword_a == "碳交易"
        assert ctx.keyword_b == "低碳"
        assert ctx.position == 100

    def test_default_count_is_one(self):
        ctx = CooccurrenceContext(
            keyword_a="a", keyword_b="b", context="c", position=0
        )
        assert ctx.count == 1

    def test_explicit_count(self):
        ctx = CooccurrenceContext(
            keyword_a="a", keyword_b="b", context="c", position=0, count=5
        )
        assert ctx.count == 5


class TestTCFDValidationResult:
    def test_create_with_required_field(self):
        r = TCFDValidationResult(is_tcfd_related=True)
        assert r.is_tcfd_related is True
        assert r.dimension == "无"
        assert r.reason == ""

    def test_create_full(self):
        r = TCFDValidationResult(
            is_tcfd_related=True, dimension="政策", reason="符合TCFD"
        )
        assert r.dimension == "政策"

    def test_reason_max_length_100(self):
        r = TCFDValidationResult(is_tcfd_related=True, reason="x" * 100)
        assert len(r.reason) == 100

    def test_reason_over_100_rejected(self):
        with pytest.raises(ValidationError):
            TCFDValidationResult(is_tcfd_related=True, reason="x" * 101)


class TestEvaluationResult:
    def test_create(self):
        r = EvaluationResult(
            keyword_a="a", keyword_b="b", context="c", position=0,
            is_tcfd_related=False, reason="不相关"
        )
        assert r.is_tcfd_related is False
        assert r.reason == "不相关"

    def test_reason_max_length_50(self):
        r = EvaluationResult(
            keyword_a="a", keyword_b="b", context="c", position=0,
            is_tcfd_related=False, reason="x" * 50
        )
        assert len(r.reason) == 50

    def test_reason_over_50_rejected(self):
        with pytest.raises(ValidationError):
            EvaluationResult(
                keyword_a="a", keyword_b="b", context="c", position=0,
                is_tcfd_related=False, reason="x" * 51
            )


class TestFileParseResult:
    def test_create(self):
        contexts = [
            CooccurrenceContext(
                keyword_a="a", keyword_b="b", context="c", position=0
            )
        ]
        r = FileParseResult(
            file="test.md", company="公司", year=2020, contexts=contexts
        )
        assert r.company == "公司"
        assert r.year == 2020
        assert len(r.contexts) == 1

    def test_empty_contexts(self):
        r = FileParseResult(
            file="test.md", company="公司", year=2020, contexts=[]
        )
        assert r.contexts == []