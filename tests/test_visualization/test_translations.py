"""Tests for Chinese → English keyword translations."""
import json
from pathlib import Path

from tcfd_extractor.visualization.translations import (
    KEYWORD_TRANSLATIONS,
    translate,
    is_translated,
    missing_translations_for,
)


class TestTranslate:
    def test_known_keyword_translated(self):
        assert translate("碳交易") == "Carbon Trading"
        assert translate("低碳") == "Low-Carbon"
        assert translate("环保") == "Environmental Protection"

    def test_unknown_keyword_returns_zh_marker(self):
        result = translate("某未知关键词")
        assert "某未知关键词" in result
        assert result.startswith("[ZH:")

    def test_translate_exact_match(self):
        assert translate("碳交易") == "Carbon Trading"


class TestIsTranslated:
    def test_known_keyword_is_translated(self):
        assert is_translated("碳交易") is True
        assert is_translated("低碳") is True

    def test_unknown_keyword_not_translated(self):
        assert is_translated("xyz_random_keyword") is False
        assert is_translated("某未知词") is False


class TestMissingTranslationsFor:
    def test_returns_untranslated_keywords(self):
        keywords = ["碳交易", "低碳", "xyz_unknown", "某未知词"]
        missing = missing_translations_for(keywords)
        assert "碳交易" not in missing
        assert "低碳" not in missing
        assert "xyz_unknown" in missing
        assert "某未知词" in missing

    def test_empty_list(self):
        assert missing_translations_for([]) == []

    def test_deduplicates(self):
        keywords = ["xyz_a", "xyz_a", "xyz_b"]
        missing = missing_translations_for(keywords)
        assert len(missing) == 2


class TestDictionaryQuality:
    def test_no_empty_keys_or_values(self):
        for zh, en in KEYWORD_TRANSLATIONS.items():
            assert zh, f"empty key: {zh!r}"
            assert en, f"empty value for {zh!r}"

    def test_translations_are_ascii_printable(self):
        for zh, en in KEYWORD_TRANSLATIONS.items():
            assert all(ord(c) < 128 for c in en), f"non-ASCII in {zh!r}: {en!r}"

    def test_translations_length_reasonable(self):
        for zh, en in KEYWORD_TRANSLATIONS.items():
            assert len(en) <= 80, f"too long: {zh!r} -> {en!r}"
            assert len(en) >= 2, f"too short: {zh!r} -> {en!r}"


class TestCoverageAgainstRealData:
    """Spec §8: ≥ 95% coverage of keywords appearing ≥ 10 times must have translations."""

    def test_high_frequency_keywords_have_translations(self, tmp_path):
        """If a keyword appears ≥ 10 times in the data, it must be translated."""
        results_dir = tmp_path / "evaluate_cooccurrence" / "2020"
        results_dir.mkdir(parents=True)
        records = []
        for _ in range(11):
            records.append({
                "file": "x.md", "keyword_a": "碳交易", "keyword_b": "低碳",
                "context": "ctx", "is_tcfd_related": True, "dimension": "政策",
                "reason": "r",
            })
        records.append({
            "file": "y.md", "keyword_a": "某生僻词", "keyword_b": "环保",
            "context": "ctx", "is_tcfd_related": False, "dimension": "无",
            "reason": "r",
        })
        (results_dir / "results.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in records),
            encoding="utf-8",
        )

        from tcfd_extractor.visualization.data_loader import load_all_results
        from tcfd_extractor.visualization.translations import is_translated, missing_translations_for

        results = load_all_results(tmp_path / "evaluate_cooccurrence")
        keyword_counter: dict[str, int] = {}
        for r in results:
            for kw in (r.get("keyword_a", ""), r.get("keyword_b", "")):
                keyword_counter[kw] = keyword_counter.get(kw, 0) + 1

        high_freq = [kw for kw, count in keyword_counter.items() if count >= 10]
        missing = missing_translations_for(high_freq)
        assert missing == [], f"High-freq keywords missing translations: {missing}"
        assert is_translated("碳交易")