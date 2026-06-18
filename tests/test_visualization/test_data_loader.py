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


def test_load_sunburst_data_returns_3_dim_tree(tmp_path):
    """Sunburst: 3 维根 → 聚类 → 关键词 三层树。

    真实 cluster JSON 格式: 顶层 list, 每项 {cluster_id, keywords, size, math_label}
    文件名: {政策维度,市场维度,技术维度}_clusters.json
    """
    # 构造最小 cluster JSON (匹配真实 schema)
    clusters_dir = tmp_path / "phase5_category_mapping"
    clusters_dir.mkdir()
    (clusters_dir / "政策维度_clusters.json").write_text(json.dumps([
        {"cluster_id": 0, "math_label": "聚类A", "keywords": ["词1", "词2"], "size": 2},
        {"cluster_id": 1, "math_label": "聚类B", "keywords": ["词3"], "size": 1},
    ], ensure_ascii=False))
    (clusters_dir / "市场维度_clusters.json").write_text(json.dumps([
        {"cluster_id": 0, "math_label": "聚类C", "keywords": ["词4"], "size": 1},
    ], ensure_ascii=False))
    (clusters_dir / "技术维度_clusters.json").write_text(json.dumps([], ensure_ascii=False))

    from tcfd_extractor.visualization.data_loader import load_sunburst_data
    result = load_sunburst_data(clusters_dir)

    assert len(result) == 3  # 3 个 dim 根
    assert result[0]["name"] == "政策"
    assert len(result[0]["children"]) == 2  # 政策有 2 聚类
    assert result[0]["children"][0]["name"] == "聚类A"  # math_label 字段
    # 技术维度 children 应为空列表 (cluster 空)
    assert result[2]["children"] == []


def test_load_streamgraph_data_aggregates_dimension_per_year(tmp_path):
    """Streamgraph: 聚合每年 results.jsonl 的 dimension 字段 (is_tcfd_related=true)。"""
    eval_dir = tmp_path / "evaluate_cooccurrence"
    for year, counts in [(2020, {"政策": 5, "市场": 2, "技术": 3}),
                         (2021, {"政策": 7, "市场": 1, "技术": 4})]:
        year_dir = eval_dir / str(year)
        year_dir.mkdir(parents=True)
        rows = []
        for dim, n in counts.items():
            for _ in range(n):
                rows.append({"dimension": dim, "is_tcfd_related": True})
        with (year_dir / "results.jsonl").open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    from tcfd_extractor.visualization.data_loader import load_streamgraph_data
    result = load_streamgraph_data(eval_dir, years=[2020, 2021])

    assert result["years"] == [2020, 2021]
    assert len(result["series"]) == 3  # 3 个 dim
    policy_series = next(s for s in result["series"] if s["name"] == "政策")
    assert policy_series["data"] == [5, 7]


def test_load_network_data_dedupes_and_clamps_symbol_size(tmp_path):
    """Force-directed: 节点去重 + symbolSize clamp [10, 60]。"""
    eval_dir = tmp_path / "evaluate_cooccurrence"
    for year in [2022, 2023]:
        year_dir = eval_dir / str(year)
        year_dir.mkdir(parents=True)
        # 词A 在两条边中出现 → freq=2, symbolSize=10+2*0.5=11
        # 词B 在一条边中出现 → freq=1, symbolSize=10+0.5=10.5→10 (clamp)
        # 词C 极高频 → freq=200, symbolSize clamp 60
        rows = [
            {"keyword_a": "词A", "keyword_b": "词B", "dimension": "政策"},
            {"keyword_a": "词A", "keyword_b": "词C", "dimension": "政策"},
            {"keyword_a": "词B", "keyword_b": "词C", "dimension": "市场"},
        ] + [{"keyword_a": "词A", "keyword_b": "词C", "dimension": "政策"}] * 200  # 让 C 极高频
        with (year_dir / "results.jsonl").open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    from tcfd_extractor.visualization.data_loader import load_network_data
    result = load_network_data(eval_dir, years=[2022, 2023],
                                top_n_edges=100, min_weight=1)

    # 节点 id 唯一
    node_ids = [n["id"] for n in result["nodes"]]
    assert len(node_ids) == len(set(node_ids))

    # symbolSize 在 [10, 60]
    for n in result["nodes"]:
        assert 10 <= n["symbolSize"] <= 60, f"node {n['id']} size {n['symbolSize']} out of range"


def test_load_sankey_data_aggregates_by_year_not_company_year(tmp_path):
    """Sankey: 节点按 year 聚合 (非 company-year), 避免节点爆炸 (3000+ → ~75)。

    真实文件路径硬编码为 output/tcfd_keywords/tcfd_keywords_summary.csv。
    阶段 1/2/3 按年聚合 (25 年 × 3 阶段 = 75 节点), 阶段 4 合并为 3 节点。
    """
    import os
    from tcfd_extractor.visualization.data_loader import load_sankey_data
    # 临时设置 CWD 到 tmp_path 并构造 fake 目录结构
    os.chdir(tmp_path)
    (tmp_path / "output" / "tcfd_keywords").mkdir(parents=True)
    summary_csv = tmp_path / "output" / "tcfd_keywords" / "tcfd_keywords_summary.csv"
    summary_csv.write_text(
        '年报,政策维度,市场维度,技术维度\n'
        '万科A-2023,"碳达峰,碳中和","绿色信贷","余热余能"\n'
        '万科A-2024,"碳达峰","绿色债券","余热余能,绿氢"\n',
        encoding="utf-8"
    )
    (tmp_path / "output" / "evaluate_cooccurrence" / "2023").mkdir(parents=True)
    (tmp_path / "output" / "evaluate_cooccurrence" / "2024").mkdir(parents=True)
    for year in [2023, 2024]:
        with (tmp_path / "output" / "evaluate_cooccurrence" / str(year) / "results.jsonl").open(
            "w", encoding="utf-8"
        ) as f:
            for _ in range(10):
                f.write(json.dumps({"is_tcfd_related": True}, ensure_ascii=False) + "\n")

    result = load_sankey_data(eval_dir=tmp_path / "output" / "evaluate_cooccurrence")

    # 所有节点都有 stage{N}_ 前缀
    for n in result["nodes"]:
        assert n["name"].startswith("stage"), f"node {n['name']} missing stage prefix"
    # 阶段 1/2/3 节点 ≤ 3 年 × 3 阶段 = 9 (不是 1001 × 3 = 3003)
    stage123 = [n for n in result["nodes"]
                if n["name"].startswith("stage1_")
                or n["name"].startswith("stage2_")
                or n["name"].startswith("stage3_")]
    assert len(stage123) <= 9, f"too many stage1-3 nodes: {len(stage123)}"
    # stage4 节点 ≤ 3 (合并)
    stage4 = [n for n in result["nodes"] if n["name"].startswith("stage4_")]
    assert len(stage4) <= 3
