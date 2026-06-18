"""Tests for loading 25 years of evaluation JSONL results."""
import json
from pathlib import Path

import pytest

from tcfd_extractor.visualization.data_loader import (
    load_all_results,
    compute_kpis,
    compute_dimension_distribution,
    compute_yearly_counts,
    compute_top_keyword_pairs,
    years_with_data,
)


@pytest.fixture
def sample_results_dir(tmp_path: Path) -> Path:
    """Create a small fake results directory with 3 years × 2 files."""
    base = tmp_path / "evaluate_cooccurrence"
    base.mkdir()
    for year in [2020, 2021, 2022]:
        year_dir = base / str(year)
        year_dir.mkdir()
        for i, (kw_a, kw_b, is_tcfd, dim) in enumerate([
            ("碳交易", "低碳", True, "政策"),
            ("环保", "风险", False, "无"),
        ]):
            record = {
                "file": f"{year:06d}-company-{year}年年度报告.md",
                "keyword_a": kw_a,
                "keyword_b": kw_b,
                "context": f"context {i}",
                "is_tcfd_related": is_tcfd,
                "dimension": dim,
                "reason": "reason",
            }
            with (year_dir / "results.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return base


class TestLoadAllResults:
    def test_loads_all_years(self, sample_results_dir):
        results = load_all_results(sample_results_dir)
        assert len(results) == 6

    def test_includes_year_field(self, sample_results_dir):
        results = load_all_results(sample_results_dir)
        years = {r["_year"] for r in results}
        assert years == {2020, 2021, 2022}

    def test_empty_directory_returns_empty_list(self, tmp_path):
        results = load_all_results(tmp_path)
        assert results == []

    def test_skips_malformed_json_lines(self, tmp_path):
        year_dir = tmp_path / "2020"
        year_dir.mkdir()
        (year_dir / "results.jsonl").write_text(
            '{"valid": true, "is_tcfd_related": true, "dimension": "政策"}\n'
            'NOT VALID JSON\n'
            '{"valid": true, "is_tcfd_related": false, "dimension": "无"}\n',
            encoding="utf-8",
        )
        results = load_all_results(tmp_path)
        assert len(results) == 2


class TestYearsWithData:
    def test_returns_years_with_records(self, sample_results_dir):
        years = years_with_data(sample_results_dir)
        assert years == [2020, 2021, 2022]

    def test_empty_dir(self, tmp_path):
        assert years_with_data(tmp_path) == []


class TestComputeKpis:
    def test_kpis_with_sample(self, sample_results_dir):
        results = load_all_results(sample_results_dir)
        kpis = compute_kpis(results)
        assert kpis["total_records"] == 6
        assert kpis["tcfd_count"] == 3
        assert kpis["total_companies"] == 3

    def test_kpis_empty(self):
        kpis = compute_kpis([])
        assert kpis["total_records"] == 0
        assert kpis["tcfd_count"] == 0


class TestComputeDimensionDistribution:
    def test_dimension_counts(self, sample_results_dir):
        results = load_all_results(sample_results_dir)
        dist = compute_dimension_distribution(results)
        assert dist["政策"] == 3
        assert dist["无"] == 3
        assert dist.get("市场", 0) == 0

    def test_returns_all_four_dimensions_present(self, sample_results_dir):
        results = load_all_results(sample_results_dir)
        dist = compute_dimension_distribution(results)
        for d in ["政策", "市场", "技术", "无"]:
            assert d in dist


class TestComputeYearlyCounts:
    def test_yearly_aggregation(self, sample_results_dir):
        results = load_all_results(sample_results_dir)
        yearly = compute_yearly_counts(results)
        assert 2020 in yearly
        assert yearly[2020]["total"] == 2
        assert yearly[2020]["tcfd"] == 1

    def test_returns_sorted_years(self, sample_results_dir):
        results = load_all_results(sample_results_dir)
        yearly = compute_yearly_counts(results)
        assert list(yearly.keys()) == sorted(yearly.keys())


class TestComputeTopKeywordPairs:
    def test_top_pairs_ranked(self, sample_results_dir):
        results = load_all_results(sample_results_dir)
        top = compute_top_keyword_pairs(results, n=5)
        assert len(top) == 2
        assert all(count == 3 for _, count in top)

    def test_top_n_limits_results(self, sample_results_dir):
        results = load_all_results(sample_results_dir)
        top = compute_top_keyword_pairs(results, n=1)
        assert len(top) == 1
