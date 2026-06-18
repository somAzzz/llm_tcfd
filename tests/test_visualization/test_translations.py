"""Tests for Chinese → English keyword translations."""
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