"""End-to-end tests for html_assembler."""
import json
from pathlib import Path

import pytest

from tcfd_extractor.visualization.html_assembler import assemble_html
from tcfd_extractor.visualization.static_charts import build_module_graph_svg


def _make_min_results(tmp_path: Path) -> Path:
    base = tmp_path / "evaluate_cooccurrence"
    year_dir = base / "2020"
    year_dir.mkdir(parents=True)
    (year_dir / "results.jsonl").write_text(
        json.dumps(
            {
                "file": "x.md", "keyword_a": "碳交易", "keyword_b": "低碳",
                "context": "ctx", "is_tcfd_related": True, "dimension": "政策",
                "reason": "r",
            },
            ensure_ascii=False,
        ) + "\n"
        + json.dumps(
            {
                "file": "y.md", "keyword_a": "环保", "keyword_b": "风险",
                "context": "ctx", "is_tcfd_related": False, "dimension": "无",
                "reason": "r",
            },
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )
    return base


class TestAssembleHtml:
    def test_produces_non_empty_html(self, tmp_path):
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            module_graph_svg=build_module_graph_svg({"config": [], "evaluator": ["config"]}),
        )
        assert len(html) > 1000
        assert "<html" in html.lower()
        assert "</html>" in html.lower()

    def test_kpis_appear_in_html(self, tmp_path):
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            module_graph_svg="<svg></svg>",
            refactor_stats={"test_after": 165, "test_before": 16},
        )
        assert ">2<" in html  # companies from the fixture's two file ids
        assert ">1<" in html  # one TCFD-related disclosure
        assert "2020" in html
        assert "165 tests passing" in html

    def test_accepts_prebuilt_report_data_bundle(self, tmp_path):
        from tcfd_extractor.visualization.html_assembler import build_report_data_bundle
        results = _make_min_results(tmp_path)
        bundle = build_report_data_bundle(
            results_root=results,
            streamgraph_years=[2020],
            network_years=[2020],
            refactor_stats={"test_after": 7, "test_before": 1},
        )
        html = assemble_html(results_root=results, data_bundle=bundle)
        assert "7 tests passing" in html
        assert "window.__hrContextIndex" in html

    def test_english_titles_present(self, tmp_path):
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            module_graph_svg="<svg></svg>",
        )
        assert "Climate Risk Intelligence" in html
        assert "From filings to climate-risk evidence" in html
        assert "A pipeline built for noisy disclosure text" in html
        assert "The signal is temporal, then linguistic" in html
        assert "Turning stochastic LLM output into a repeatable artifact" in html

    def test_portfolio_insight_cards_included(self, tmp_path):
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            module_graph_svg="<svg></svg>",
        )
        assert "Portfolio case file" in html
        assert "Evidence extracted from annual-report language" in html
        assert "Disclosure acceleration" in html
        assert "Policy-led signal" in html
        assert "Engineering proof" in html

    def test_top_keyword_pairs_panel_included(self, tmp_path):
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            module_graph_svg="<svg></svg>",
        )
        assert "evidence-list" in html
        assert "Low-Carbon / Carbon Trading" in html
        assert "低碳" not in html
        assert "碳交易" not in html

    def test_charts_json_inlined(self, tmp_path):
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            module_graph_svg="<svg></svg>",
        )
        assert 'id="echarts-sunburst"' in html
        assert 'id="echarts-streamgraph"' in html
        assert 'id="echarts-network"' in html
        assert 'id="echarts-sankey"' in html

    def test_assembled_html_has_4_echarts_charts(self, tmp_path):
        """集成测试: 生成的 HTML 含 4 个 ECharts 初始化块 (Stage 2: 通过 buildChart 统一管理, rebuildAllCharts 触发 4 次)。"""
        from tcfd_extractor.visualization.html_assembler import assemble_html
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            module_graph_svg="<svg></svg>",
            refactor_stats={"god_class_before": 0, "god_class_after": 0, "module_count": 0,
                            "total_lines": 0, "test_before": 0, "test_after": 0},
        )
        assert "echarts.init" in html
        # Stage 2: 1 个 buildChart() 函数 + 4 次 buildChart 调用 (sunburst + streamgraph + network + sankey)
        assert html.count("buildChart(") >= 4
        # 4 个 chart container div id
        for cid in ("echarts-sunburst", "echarts-streamgraph", "echarts-network", "echarts-sankey"):
            assert f"'{cid}'" in html or f'"{cid}"' in html
        # ECharts CDN 引用
        assert "echarts@5" in html

    def test_marketing_callout_included(self, tmp_path):
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            module_graph_svg="<svg></svg>",
        )
        assert "Reusable pattern" in html
        assert "Public-safe output" in html

    def test_module_graph_inlined(self, tmp_path):
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            module_graph_svg="",
        )
        assert "echarts-module-graph" in html
        assert "Module dependency graph" in html

    def test_pipeline_health_chart_inlined(self, tmp_path):
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            module_graph_svg="<svg></svg>",
        )
        assert "echarts-pipeline-health-dashboard" in html
        assert "Structured validation" in html
        assert "Streaming and concurrency" in html
        assert "Publication checks" in html
        assert "pipelineHealthDashboard" in html


class TestBuildContextIndex:
    """Spec §8: build_context_index — 关键词索引 / sankey 边索引 / 3 sample cap。"""

    def _make_results(self, tmp_path: Path) -> Path:
        base = tmp_path / "evaluate_cooccurrence"
        year_dir = base / "2023"
        year_dir.mkdir(parents=True)
        records = []
        # 同一关键词 4 次出现, 应 cap 到 3 条
        for i in range(4):
            records.append({
                "file": f"x{i}.md", "keyword_a": "碳交易", "keyword_b": "低碳",
                "context": f"ctx {i}", "is_tcfd_related": True, "dimension": "政策",
            })
        # 第二组, 另一对
        records.append({
            "file": "y.md", "keyword_a": "环保", "keyword_b": "碳市场",
            "context": "ctx env", "is_tcfd_related": True, "dimension": "市场",
        })
        # 不相关 → 不进索引
        records.append({
            "file": "z.md", "keyword_a": "x", "keyword_b": "y",
            "context": "ctx", "is_tcfd_related": False, "dimension": "无",
        })
        (year_dir / "results.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in records),
            encoding="utf-8",
        )
        return base

    def test_keywords_index_caps_at_3_samples(self, tmp_path):
        from tcfd_extractor.visualization.html_assembler import build_context_index
        results = self._make_results(tmp_path)
        index = build_context_index(eval_dir=results, years=[2023])
        assert len(index["keywords"]["Carbon Trading"]) == 3
        assert len(index["keywords"]["Low-Carbon"]) == 3

    def test_sankey_index_uses_sorted_edge_key(self, tmp_path):
        from tcfd_extractor.visualization.html_assembler import build_context_index
        results = self._make_results(tmp_path)
        index = build_context_index(eval_dir=results, years=[2023])
        assert "Carbon Trading->Low-Carbon" in index["sankey"]
        assert "Low-Carbon->Carbon Trading" not in index["sankey"]
        assert "Carbon Market->Environmental Protection" in index["sankey"]
        assert "Environmental Protection->Carbon Market" not in index["sankey"]

    def test_sankey_index_includes_pipeline_stage_edges(self, tmp_path):
        from tcfd_extractor.visualization.html_assembler import build_context_index
        results = self._make_results(tmp_path)
        index = build_context_index(eval_dir=results, years=[2023])
        assert "Reports 2023->Chunks 2023" in index["sankey"]
        assert "Chunks 2023->Disclosures 2023" in index["sankey"]
        assert "Disclosures 2023->Policy Keywords" in index["sankey"]
        assert "Disclosures 2023->Market Keywords" in index["sankey"]

    def test_unrelated_records_excluded(self, tmp_path):
        from tcfd_extractor.visualization.html_assembler import build_context_index
        results = self._make_results(tmp_path)
        index = build_context_index(eval_dir=results, years=[2023])
        # is_tcfd_related=False 的 x/y 不进索引
        assert "x" not in index["keywords"]
        assert "y" not in index["keywords"]


class TestPortfolioInsights:
    def test_build_portfolio_insights_highlights_growth_and_dimensions(self):
        from tcfd_extractor.visualization.html_assembler import build_portfolio_insights

        records = [
            {"_year": 2000, "is_tcfd_related": True, "dimension": "政策"},
            {"_year": 2024, "is_tcfd_related": True, "dimension": "政策"},
            {"_year": 2024, "is_tcfd_related": True, "dimension": "技术"},
            {"_year": 2024, "is_tcfd_related": False, "dimension": "无"},
        ]
        insights = build_portfolio_insights(records)
        assert [i["label"] for i in insights] == [
            "Disclosure acceleration",
            "Policy-led signal",
            "Engineering proof",
        ]
        assert insights[0]["value"] == "1 -> 2"
        assert insights[1]["value"] == "2"

    def test_build_top_keyword_pairs_returns_translated_counts(self):
        from tcfd_extractor.visualization.html_assembler import build_top_keyword_pairs

        records = [
            {"is_tcfd_related": True, "keyword_a": "环保", "keyword_b": "风险"},
            {"is_tcfd_related": True, "keyword_a": "风险", "keyword_b": "环保"},
            {"is_tcfd_related": True, "keyword_a": "碳交易", "keyword_b": "低碳"},
            {"is_tcfd_related": False, "keyword_a": "x", "keyword_b": "y"},
        ]
        pairs = build_top_keyword_pairs(records, limit=2)
        assert pairs[0]["pair"] == "Environmental Protection / Risk"
        assert pairs[0]["full_pair"] == "Environmental Protection / Risk"
        assert pairs[0]["count"] == "2"
        assert pairs[0]["translated"] == (
            "2 records link this pair as risk language in management discussion."
        )


class TestContextInjection:
    """Spec §5.3 + §8: 注入 window.__hrTranslateMap 和 window.__hrContextIndex。"""

    def test_translate_map_injected(self, tmp_path):
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            module_graph_svg="<svg></svg>",
        )
        assert "window.__hrTranslateMap" in html
        # 含已知英文
        assert "Carbon Trading" in html
        assert "Policy" in html

    def test_context_index_injected(self, tmp_path):
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            module_graph_svg="<svg></svg>",
        )
        assert "window.__hrContextIndex" in html


class TestStage2TemplateContent:
    """Spec §11 集成测试: Inter 字体 + Alpine + 暗色默认 + 侧栏。"""

    def test_html_has_dark_theme_default(self, tmp_path):
        """<html data-theme='dark'> 暗色默认。"""
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            module_graph_svg="<svg></svg>",
        )
        assert 'data-theme="dark"' in html

    def test_html_has_portfolio_font_links(self, tmp_path):
        """Portfolio font system appears with display=swap."""
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            module_graph_svg="<svg></svg>",
        )
        assert "Fraunces" in html
        assert "IBM+Plex+Sans" in html
        assert "JetBrains+Mono" in html
        assert "display=swap" in html

    def test_html_has_alpine_defer_script(self, tmp_path):
        """Alpine.js <script defer> 出现, URL 锁版本 3.13.x。"""
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            module_graph_svg="<svg></svg>",
        )
        assert "alpinejs@3.13" in html
        assert "defer" in html

    def test_html_has_side_panel_with_zindex(self, tmp_path):
        """<aside> 侧栏 + z-index 1000 + backdrop 出现。"""
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            module_graph_svg="<svg></svg>",
        )
        assert "hr-side-panel" in html
        assert "z-index: 1000" in html
        assert "hr-side-panel-backdrop" in html


class TestDataclassDefaultEncoder:
    """_dataclass_default JSON encoder: serialize PipelineMetric instances
    that build_pipeline_health_dashboard embeds in bar data."""

    def test_serializes_dataclass_to_dict(self):
        from dataclasses import dataclass
        from tcfd_extractor.visualization.html_assembler import _dataclass_default

        @dataclass
        class Point:
            x: int
            y: int

        result = _dataclass_default(Point(3, 4))
        assert result == {"x": 3, "y": 4}

    def test_rejects_non_dataclass(self):
        from tcfd_extractor.visualization.html_assembler import _dataclass_default

        with pytest.raises(TypeError):
            _dataclass_default("not a dataclass")

    def test_serializes_real_pipeline_metric(self):
        """The full path: build_pipeline_health_dashboard embeds PipelineMetric
        in bar data, which json.dumps must serialize via _dataclass_default."""
        import json as _json
        from tcfd_extractor.visualization.html_assembler import _dataclass_default
        from tcfd_extractor.visualization.echarts import build_pipeline_health_dashboard
        from tcfd_extractor.visualization.pipeline_metrics import (
            ALL_STATIC_METRICS, TEST_COVERAGE_TEMPLATE, PipelineMetric,
        )

        test_coverage = PipelineMetric(
            name=TEST_COVERAGE_TEMPLATE.name,
            unit=TEST_COVERAGE_TEMPLATE.unit,
            before=16,
            after=329,
            note=TEST_COVERAGE_TEMPLATE.note,
        )
        metrics = (*ALL_STATIC_METRICS, test_coverage)
        opt = build_pipeline_health_dashboard(metrics, {"text_style": {"color": "#fff"}, "colors": {"tech": "#0f0"}})

        # Without the encoder, this would raise TypeError on the PipelineMetric instances.
        json_str = _json.dumps(opt, default=_dataclass_default)
        parsed = _json.loads(json_str)
        # First bar's metric should be a dict with all dataclass fields
        assert parsed["series"][0]["data"][0]["metric"]["name"] == "Memory Footprint"
        assert parsed["series"][0]["data"][0]["metric"]["unit"] == "GB"
