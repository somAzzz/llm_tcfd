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
    # Stage 3 修复: dim/cluster/keyword 全部英文化
    assert result[0]["name"] == "Policy"
    assert result[1]["name"] == "Market"
    assert result[2]["name"] == "Technology"
    assert len(result[0]["children"]) == 2  # 政策有 2 聚类
    # 聚类名 (math_label) 翻译为英文
    assert result[0]["children"][0]["name"] == "Cluster A"
    assert result[0]["children"][1]["name"] == "Cluster B"
    assert result[1]["children"][0]["name"] == "Cluster C"
    # 关键词也翻译
    assert result[0]["children"][0]["children"][0]["name"] == "词1"  # 不在 dict, 保留原文
    # 技术维度 children 应为空列表 (cluster 空)
    assert result[2]["children"] == []


def test_load_sunburst_translates_realistic_chinese_math_labels(tmp_path):
    """Stage 3 修复: 真实 cluster JSON 的 math_label 是描述性中文 (e.g. 排放限值),
    不在 KEYWORD_TRANSLATIONS, 应 fallback 到 'Cluster {id}' 而不是 [[ZH: ...]]。
    """
    from tcfd_extractor.visualization.data_loader import load_sunburst_data
    clusters_dir = tmp_path / "phase5_category_mapping"
    clusters_dir.mkdir()
    (clusters_dir / "政策维度_clusters.json").write_text(json.dumps([
        {"cluster_id": 0, "math_label": "排放限值", "keywords": ["VOCs"], "size": 1},
        {"cluster_id": 1, "math_label": "节能减排", "keywords": ["节能"], "size": 1},
        {"cluster_id": 2, "math_label": "未知中文标签XYZ", "keywords": ["x"], "size": 1},
    ], ensure_ascii=False))
    (clusters_dir / "市场维度_clusters.json").write_text(json.dumps([], ensure_ascii=False))
    (clusters_dir / "技术维度_clusters.json").write_text(json.dumps([], ensure_ascii=False))

    result = load_sunburst_data(clusters_dir)

    # Stage 4 修复: 93 个真实 math_label 全部进 dict, 应直接显示英文
    cluster_names = [c["name"] for c in result[0]["children"]]
    # 排放限值 现在在 dict → "Emission Cap"
    assert "Emission Cap" in cluster_names
    # 节能减排 在 dict 中 → "Energy Saving & Emission Reduction"
    assert "Energy Saving & Emission Reduction" in cluster_names
    # 不在 dict 的中文 → fallback "Cluster {id}"
    assert "Cluster 2" in cluster_names  # 未知中文标签XYZ
    # 不能有 [[ZH: ...]] wrapper
    for c in cluster_names:
        assert not c.startswith("[[ZH:"), f"untranslated Chinese: {c!r}"


def test_load_sunburst_data_injects_dim_color_inheritance_per_cluster(tmp_path):
    """Stage 4 颜色继承: 每个 cluster 节点必须有 itemStyle.color,
    继承父辈 dim 的颜色 (Policy=#79c0ff → rgba 半透明, Market=#ffa657 → ...,
    Technology=#7ee787 → ...) 让 cluster 层视觉上是父辈色的淡化过渡,
    而非通铺死灰。

    Stage 4 round 3: dim 颜色从 TCFD_THEME_CONFIG 派生 (而非硬编码),
    所以这里也用 echarts.TCFD_THEME_CONFIG 期望值保持一致。

    实现: load_sunburst_data 给每个 cluster 节点注入
    itemStyle.color = rgba(R, G, B, 0.4), alpha=0.4 让它与炭黑背景叠加。
    """
    from tcfd_extractor.visualization.data_loader import load_sunburst_data
    from tcfd_extractor.visualization.echarts import TCFD_THEME_CONFIG
    clusters_dir = tmp_path / "phase5_category_mapping"
    clusters_dir.mkdir()
    # 每个 dim 各一个 cluster
    (clusters_dir / "政策维度_clusters.json").write_text(json.dumps([
        {"cluster_id": 0, "math_label": "测试1", "keywords": ["x"], "size": 1},
    ], ensure_ascii=False))
    (clusters_dir / "市场维度_clusters.json").write_text(json.dumps([
        {"cluster_id": 0, "math_label": "测试2", "keywords": ["y"], "size": 1},
    ], ensure_ascii=False))
    (clusters_dir / "技术维度_clusters.json").write_text(json.dumps([
        {"cluster_id": 0, "math_label": "测试3", "keywords": ["z"], "size": 1},
    ], ensure_ascii=False))

    result = load_sunburst_data(clusters_dir)

    # 3 个 dim 各对应一个 cluster, 都必须有 itemStyle.color
    import re as _re
    rgba_re = _re.compile(r"^rgba\(\d+,\s*\d+,\s*\d+,\s*[\d.]+\)$")
    # 从 TCFD_THEME_CONFIG 派生期望值 (Stage 4 r3 改为 #79c0ff / #ffa657 / #7ee787)
    def _hex_to_rgba(hex_color, alpha=0.4):
        h = hex_color.lstrip("#")
        return f"rgba({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}, {alpha})"
    expected_colors = {
        "Policy": _hex_to_rgba(TCFD_THEME_CONFIG["colors"]["policy"]),
        "Market": _hex_to_rgba(TCFD_THEME_CONFIG["colors"]["market"]),
        "Technology": _hex_to_rgba(TCFD_THEME_CONFIG["colors"]["tech"]),
    }
    for dim_name, expected_color in expected_colors.items():
        dim = next(d for d in result if d["name"] == dim_name)
        assert dim["children"], f"{dim_name} has no clusters"
        # dim root must carry the bright per-node color (no alpha) so the
        # inner ring is unambiguously colored even when ECharts' levels[1]
        # list-cycling fails to apply (older versions / different data shapes).
        assert "itemStyle" in dim, (
            f"{dim_name} dim root missing itemStyle.color — inner ring "
            f"will fall back to the default palette or stay dark: {dim}"
        )
        assert dim["itemStyle"]["color"] == TCFD_THEME_CONFIG["colors"][
            {"Policy": "policy", "Market": "market", "Technology": "tech"}[dim_name]
        ], (
            f"{dim_name} dim root color must be the bright Primer value "
            f"({TCFD_THEME_CONFIG['colors']}), got {dim['itemStyle']['color']}"
        )
        cluster = dim["children"][0]
        assert "itemStyle" in cluster, (
            f"{dim_name} cluster missing itemStyle (color inheritance broken): {cluster}"
        )
        color = cluster["itemStyle"].get("color", "")
        assert rgba_re.match(color), (
            f"{dim_name} cluster color must be rgba(r, g, b, alpha), got: {color!r}"
        )
        assert color == expected_color, (
            f"{dim_name} cluster color should be {expected_color} (parent dim with alpha=0.4), "
            f"got: {color}"
        )


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
    # Stage 3 修复: dim 名称英文化
    policy_series = next(s for s in result["series"] if s["name"] == "Policy")
    assert policy_series["data"] == [5, 7]
    # 所有 dim 都是英文
    series_names = {s["name"] for s in result["series"]}
    assert series_names == {"Policy", "Market", "Technology"}


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

    Stage 3.2 修复: 节点名为 clean English ("Reports 2023" 等), 不再用
    stage{N}_ 前缀 (原 prefix 触发了 formatter → ECharts 把 JS 源码当 template 渲染)。
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

    # 节点名是 clean English (e.g., "Reports 2023"), 不用 stage{N}_ 前缀
    for n in result["nodes"]:
        assert not n["name"].startswith("stage"), (
            f"node {n['name']} still uses stage prefix — should be clean English"
        )
    # 阶段 1/2/3 节点 ≤ 2 年 × 3 阶段 = 6 (不是 1001 × 3 = 3003)
    stage123_keywords = {"Reports", "Chunks", "Disclosures"}
    stage123 = [n for n in result["nodes"]
                if any(n["name"].startswith(f"{kw} ") for kw in stage123_keywords)]
    assert len(stage123) <= 6, f"too many stage1-3 nodes: {len(stage123)}"
    # stage4 节点 ≤ 3 (合并为 Policy/Market/Technology Keywords)
    stage4_keywords = {"Policy Keywords", "Market Keywords", "Technology Keywords"}
    stage4 = [n for n in result["nodes"] if n["name"] in stage4_keywords]
    assert len(stage4) <= 3


def test_load_sankey_data_handles_utf8_bom_in_csv(tmp_path):
    """Regression: 真实 summary.csv 有 UTF-8 BOM, encoding 必须用 utf-8-sig。"""
    import os
    from tcfd_extractor.visualization.data_loader import load_sankey_data
    os.chdir(tmp_path)
    (tmp_path / "output" / "tcfd_keywords").mkdir(parents=True)
    # 写带 BOM 的 CSV (模拟真实文件, 文件名含 "年年度报告.txt" 才能被 parser 接受)
    summary_csv = tmp_path / "output" / "tcfd_keywords" / "tcfd_keywords_summary.csv"
    with summary_csv.open("wb") as f:
        f.write(b"\xef\xbb\xbf")  # UTF-8 BOM
        f.write('年报,政策维度,市场维度,技术维度\n'.encode("utf-8"))
        f.write('万科A-2023年年度报告.txt,"碳达峰,碳中和","绿色信贷","余热余能"\n'.encode("utf-8"))
    (tmp_path / "output" / "evaluate_cooccurrence" / "2023").mkdir(parents=True)
    (tmp_path / "output" / "evaluate_cooccurrence" / "2023" / "results.jsonl").write_text(
        '{"is_tcfd_related": true}\n', encoding="utf-8"
    )
    result = load_sankey_data(eval_dir=tmp_path / "output" / "evaluate_cooccurrence")
    assert len(result["nodes"]) > 0, "BOM CSV should still parse, got empty nodes"
    # 应该产出 3 个 stage1/2/3 节点 (1 年 × 3 阶段) — clean English names
    stage123_keywords = {"Reports", "Chunks", "Disclosures"}
    stage123 = [n for n in result["nodes"]
                if any(n["name"].startswith(f"{kw} ") for kw in stage123_keywords)]
    assert len(stage123) == 3, f"expected 3 stage1-3 nodes for year 2023, got {len(stage123)}"
    # 节点名应包含年份 2023
    assert any("2023" in n["name"] for n in result["nodes"])


def test_load_sankey_data_uses_clean_english_node_names(tmp_path):
    """Stage 3.2 修复: sankey 节点名是 clean English, ECharts 默认 {b} 直接显示。

    旧实现: `stage1_report_2023` + JS string formatter → ECharts 把 JS 源码当
    template string 渲染 (display: "function(p) { const t = ...").
    新实现: `Reports 2023` 等 clean English name + 无 formatter → ECharts 显示节点名。
    """
    import os
    from tcfd_extractor.visualization.data_loader import load_sankey_data
    os.chdir(tmp_path)
    (tmp_path / "output" / "tcfd_keywords").mkdir(parents=True)
    summary_csv = tmp_path / "output" / "tcfd_keywords" / "tcfd_keywords_summary.csv"
    summary_csv.write_text(
        '年报,政策维度,市场维度,技术维度\n'
        '万科A-2023年年度报告.txt,"碳达峰,碳中和","绿色信贷","余热余能"\n',
        encoding="utf-8"
    )
    (tmp_path / "output" / "evaluate_cooccurrence" / "2023").mkdir(parents=True)
    (tmp_path / "output" / "evaluate_cooccurrence" / "2023" / "results.jsonl").write_text(
        '{"is_tcfd_related": true}\n', encoding="utf-8"
    )
    result = load_sankey_data(eval_dir=tmp_path / "output" / "evaluate_cooccurrence")
    node_names = {n["name"] for n in result["nodes"]}

    # 4 类节点: Reports/Chunks/Disclosures + 3 dim Keywords
    assert "Reports 2023" in node_names
    assert "Chunks 2023" in node_names
    assert "Disclosures 2023" in node_names
    assert "Policy Keywords" in node_names
    assert "Market Keywords" in node_names
    assert "Technology Keywords" in node_names

    # 没有任何 stage{N}_ 前缀残留
    for name in node_names:
        assert not name.startswith("stage"), f"residual stage prefix: {name!r}"

    # 没有中文节点名 (避免 [[ZH: ...]] 之类的翻译 fallback 出现在 tooltip)
    for name in node_names:
        assert not any('\u4e00' <= c <= '\u9fff' for c in name), (
            f"Chinese char in node name: {name!r}"
        )
