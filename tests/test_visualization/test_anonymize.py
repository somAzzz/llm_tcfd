"""Tests for one-way company_id anonymization."""
from tcfd_extractor.visualization.anonymize import (
    anonymize_company_id,
    anonymize_filename,
    anonymize_record,
)


class TestAnonymizeCompanyId:
    def test_same_id_same_anonymized(self):
        assert anonymize_company_id("000001") == anonymize_company_id("000001")

    def test_different_ids_likely_different(self):
        """1000 distinct ids should map to ≥ 990 distinct anonymized values."""
        ids = [f"{i:06d}" for i in range(1000)]
        anonymized = {anonymize_company_id(i) for i in ids}
        assert len(anonymized) >= 990

    def test_anonymized_format(self):
        result = anonymize_company_id("000001")
        assert result.startswith("Company #")
        assert result.split("#")[1].isdigit()
        assert len(result.split("#")[1]) == 3

    def test_empty_string_returns_placeholder(self):
        result = anonymize_company_id("")
        assert result.startswith("Company #")

    def test_unicode_id_handled(self):
        result = anonymize_company_id("平安银行")
        assert result.startswith("Company #")

    def test_never_contains_original(self):
        original = "000001-平安银行"
        result = anonymize_company_id(original)
        assert original not in result


class TestAnonymizeFilename:
    def test_extracts_year(self):
        assert anonymize_filename("000001-平安银行-2020年年度报告.md") == "report_year2020_#001.md"

    def test_no_year_returns_placeholder(self):
        result = anonymize_filename("random.md")
        assert "year" in result.lower() or "_" in result

    def test_handles_path_like_input(self):
        result = anonymize_filename("/some/path/000001-平安银行-2020年年度报告.md")
        assert "2020" in result


class TestAnonymizeRecord:
    def test_anonymizes_file(self):
        record = {
            "file": "000001-平安银行-2020年年度报告.md",
            "keyword_a": "碳交易",
            "keyword_b": "低碳",
            "context": "公司参与碳交易",
            "is_tcfd_related": True,
            "dimension": "政策",
            "reason": "涉及碳排放权交易",
        }
        result = anonymize_record(record)
        assert "平安银行" not in result["file"]
        assert "000001-平安银行" not in result["file"]
        assert result["keyword_a"] == "碳交易"
        assert result["context"] == "公司参与碳交易"
        assert "2020" in result["file"]

    def test_truncates_long_reason(self):
        record = {"file": "x.md", "reason": "x" * 200, "is_tcfd_related": True}
        result = anonymize_record(record)
        assert len(result["reason"]) <= 80

    def test_preserves_required_fields(self):
        record = {
            "file": "x.md",
            "keyword_a": "a",
            "keyword_b": "b",
            "context": "c",
            "is_tcfd_related": True,
            "dimension": "政策",
            "reason": "r",
        }
        result = anonymize_record(record)
        for field in ("keyword_a", "keyword_b", "context", "is_tcfd_related", "dimension"):
            assert field in result