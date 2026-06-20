"""Tests for scripts/translate_report_terms.py."""
from __future__ import annotations

import json

import pytest

from scripts.translate_report_terms import (
    TranslationMap,
    collect_candidate_terms,
    english_fallback,
    parse_translation_response,
)


def test_parse_translation_response_extracts_json_after_reasoning():
    raw = """
Thinking briefly...
{"translations": {"低碳园区": "Example"}}
{"translations": {"低碳园区": "Low-Carbon Industrial Park"}}
"""
    parsed = parse_translation_response(raw, ["低碳园区"])
    assert parsed == {"低碳园区": "Low-Carbon Industrial Park"}


def test_parse_translation_response_accepts_ordered_values_when_keys_drift():
    raw = '{"translations": {"translated_key": "Market Volatility"}}'
    parsed = parse_translation_response(raw, ["波动"])
    assert parsed == {"波动": "Market Volatility"}


def test_translation_map_rejects_chinese_values():
    with pytest.raises(ValueError):
        TranslationMap(translations={"低碳园区": "低碳 Park"})


def test_translation_map_rejects_generic_placeholder_values():
    with pytest.raises(ValueError):
        TranslationMap(translations={"波动": "English Label"})


def test_english_fallback_is_stable_and_english_only():
    first = english_fallback("某未知术语")
    second = english_fallback("某未知术语")
    assert first == second
    assert first.startswith("Climate Disclosure Term ")
    assert not any("\u4e00" <= c <= "\u9fff" for c in first)


def test_collect_candidate_terms_from_report_sources(tmp_path):
    clusters_dir = tmp_path / "clusters"
    clusters_dir.mkdir()
    (clusters_dir / "政策维度_clusters.json").write_text(
        json.dumps([
            {"cluster_id": 1, "math_label": "低碳园区", "keywords": ["未知技术"], "size": 2}
        ], ensure_ascii=False),
        encoding="utf-8",
    )
    eval_dir = tmp_path / "eval"
    year_dir = eval_dir / "2024"
    year_dir.mkdir(parents=True)
    (year_dir / "results.jsonl").write_text(
        json.dumps({
            "keyword_a": "低碳园区",
            "keyword_b": "陌生设备",
            "is_tcfd_related": True,
        }, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    terms = collect_candidate_terms(
        clusters_dir=clusters_dir,
        eval_dir=eval_dir,
        years=[2024],
        include_known=False,
    )

    assert "低碳园区" in terms
    assert "未知技术" in terms
    assert "陌生设备" in terms
