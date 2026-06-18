"""Assembles the final HTML by rendering the Jinja2 template with all data."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from .data_loader import (
    compute_dimension_distribution,
    compute_kpis,
    compute_top_keyword_pairs,
    compute_yearly_counts,
    load_all_results,
    years_with_data,
)
from .template import HTML_TEMPLATE


def assemble_html(
    results_root: Path,
    *,
    refactor_bar_b64: str,
    module_graph_svg: str,
    refactor_stats: dict | None = None,
    build_date: str | None = None,
) -> str:
    """Load data, build charts, render template. Returns final HTML string.

    Args:
        results_root: Path to evaluate_cooccurrence/ directory
        refactor_bar_b64: base64 PNG of the refactor before/after chart
        module_graph_svg: SVG string of the module dependency graph
        refactor_stats: optional dict:
            {"test_after": int, ...} — used to compute KPI test summary
        build_date: ISO date string; defaults to today
    """
    from .chart_builders import build_donut, build_top_keyword_bar, build_yearly_trend

    results = load_all_results(results_root)
    kpis_raw = compute_kpis(results)
    years = years_with_data(results_root)
    years_range = f"{min(years)}–{max(years)}" if years else "N/A"
    test_count = (refactor_stats or {}).get("test_after", 0)
    kpis = {
        **kpis_raw,
        "years_range": years_range,
        "test_summary": f"{test_count} tests passing" if test_count else "tests passing",
    }

    distribution = compute_dimension_distribution(results)
    donut_fig = build_donut(distribution)
    donut_json = donut_fig.to_json()

    yearly = compute_yearly_counts(results)
    trend_fig = build_yearly_trend(yearly)
    trend_json = trend_fig.to_json()

    pairs = compute_top_keyword_pairs(results, n=10)
    bar_fig = build_top_keyword_bar(pairs)
    bar_json = bar_fig.to_json()

    return HTML_TEMPLATE.render(
        kpis=kpis,
        donut_json=donut_json,
        trend_json=trend_json,
        bar_json=bar_json,
        refactor_b64=refactor_bar_b64,
        module_graph_svg=module_graph_svg,
        refactor_stats=refactor_stats or {},
        build_date=build_date or date.today().isoformat(),
    )