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
        assert "2020" in html
        assert "165" in html

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
        assert 'id="donut-data"' in html
        assert 'id="trend-data"' in html
        assert 'id="bar-data"' in html

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