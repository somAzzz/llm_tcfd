"""End-to-end tests for html_assembler."""
import json
from pathlib import Path

from tcfd_extractor.visualization.html_assembler import assemble_html
from tcfd_extractor.visualization.static_charts import (
    build_module_graph_svg,
    build_refactor_bar,
)


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
            refactor_bar_b64=build_refactor_bar(468, 79, 1004, 10, 16, 165),
            module_graph_svg=build_module_graph_svg({"config": [], "evaluator": ["config"]}),
        )
        assert len(html) > 1000
        assert "<html" in html.lower()
        assert "</html>" in html.lower()

    def test_kpis_appear_in_html(self, tmp_path):
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            refactor_bar_b64="x",
            module_graph_svg="<svg></svg>",
            refactor_stats={"test_after": 165, "test_before": 16},
        )
        assert "10,814" in html  # companies
        assert "165 tests passing" in html

    def test_english_titles_present(self, tmp_path):
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            refactor_bar_b64="x",
            module_graph_svg="<svg></svg>",
        )
        assert "What is this project" in html
        assert "What we built" in html
        assert "What we discovered" in html
        assert "Engineering excellence" in html

    def test_charts_json_inlined(self, tmp_path):
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            refactor_bar_b64="x",
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
            refactor_bar_b64="iVBORw0KGgoAAAANSUhEUgAA",
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
            refactor_bar_b64="x",
            module_graph_svg="<svg></svg>",
        )
        assert "Beyond TCFD" in html
        assert "Reusable Architecture" in html

    def test_module_graph_inlined(self, tmp_path):
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            refactor_bar_b64="x",
            module_graph_svg='<svg id="my-graph"></svg>',
        )
        assert "my-graph" in html
        assert "Tech Deep Dive" in html

    def test_refactor_chart_inlined(self, tmp_path):
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            refactor_bar_b64="iVBORw0KGgoAAAANSUhEUgAA",
            module_graph_svg="<svg></svg>",
        )
        assert "data:image/png;base64,iVBORw" in html


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
        # 碳交易/低碳 4 条 → cap 到 3
        assert len(index["keywords"]["碳交易"]) == 3
        assert len(index["keywords"]["低碳"]) == 3

    def test_sankey_index_uses_sorted_edge_key(self, tmp_path):
        from tcfd_extractor.visualization.html_assembler import build_context_index
        results = self._make_results(tmp_path)
        index = build_context_index(eval_dir=results, years=[2023])
        # sankey 边 key: 排序后的 a->b
        # 注: sorted(["碳交易", "低碳"]) == ["低碳", "碳交易"] 因为 "低"(U+4F4E) < "碳"(U+78B3)
        assert "低碳->碳交易" in index["sankey"]
        assert "碳交易->低碳" not in index["sankey"]  # 只存正序
        # 第二组: 环保 ↔ 碳市场
        assert "环保->碳市场" in index["sankey"]
        assert "碳市场->环保" not in index["sankey"]

    def test_unrelated_records_excluded(self, tmp_path):
        from tcfd_extractor.visualization.html_assembler import build_context_index
        results = self._make_results(tmp_path)
        index = build_context_index(eval_dir=results, years=[2023])
        # is_tcfd_related=False 的 x/y 不进索引
        assert "x" not in index["keywords"]
        assert "y" not in index["keywords"]


class TestContextInjection:
    """Spec §5.3 + §8: 注入 window.__hrTranslateMap 和 window.__hrContextIndex。"""

    def test_translate_map_injected(self, tmp_path):
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            refactor_bar_b64="x",
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
            refactor_bar_b64="x",
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
            refactor_bar_b64="x",
            module_graph_svg="<svg></svg>",
        )
        assert 'data-theme="dark"' in html

    def test_html_has_inter_font_link(self, tmp_path):
        """Inter Google Fonts <link> 出现, 含 display=swap。"""
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            refactor_bar_b64="x",
            module_graph_svg="<svg></svg>",
        )
        assert "Inter:wght" in html
        assert "display=swap" in html

    def test_html_has_alpine_defer_script(self, tmp_path):
        """Alpine.js <script defer> 出现, URL 锁版本 3.13.x。"""
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            refactor_bar_b64="x",
            module_graph_svg="<svg></svg>",
        )
        assert "alpinejs@3.13" in html
        assert "defer" in html

    def test_html_has_side_panel_with_zindex(self, tmp_path):
        """<aside> 侧栏 + z-index 1000 + backdrop 出现。"""
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            refactor_bar_b64="x",
            module_graph_svg="<svg></svg>",
        )
        assert "hr-side-panel" in html
        assert "z-index: 1000" in html
        assert "hr-side-panel-backdrop" in html