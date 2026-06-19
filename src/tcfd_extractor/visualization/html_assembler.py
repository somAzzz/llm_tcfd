"""Assembles the final HTML by rendering the Jinja2 template with all data."""
from __future__ import annotations

import json as _json
import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

from .data_loader import (
    load_network_data,
    load_sankey_data,
    load_streamgraph_data,
    load_sunburst_data,
)
from .echarts import (
    TCFD_THEME_CONFIG,
    build_network,
    build_sankey,
    build_streamgraph,
    build_sunburst,
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
        refactor_stats: optional dict (preserved for template)
        build_date: ISO date string; defaults to today
    """
    clusters_dir = Path("output/tcfd_keywords/phase5_category_mapping")
    eval_dir = results_root  # results_root 就是 evaluate_cooccurrence 目录

    sunburst_opt = build_sunburst(load_sunburst_data(clusters_dir), TCFD_THEME_CONFIG)
    streamgraph_opt = build_streamgraph(
        load_streamgraph_data(eval_dir, years=range(2000, 2025)), TCFD_THEME_CONFIG
    )
    network_opt = build_network(
        load_network_data(eval_dir, years=[2022, 2023, 2024]), TCFD_THEME_CONFIG
    )
    # Sankey 路径 hardcode (load_sankey_data 内部默认读 output/tcfd_keywords/tcfd_keywords_summary.csv)
    # 若数据缺失则降级为占位 option, 不阻塞 HTML 渲染
    try:
        sankey_opt = build_sankey(load_sankey_data(eval_dir=eval_dir), TCFD_THEME_CONFIG)
    except (FileNotFoundError, KeyError, ValueError) as e:
        logger.warning("Sankey: load_sankey_data failed (%s: %s), rendering empty sankey",
                       type(e).__name__, e)
        sankey_opt = {"series": [{"type": "sankey", "data": [], "links": []}]}

    # 4 个 option 序列化为 JSON 字符串 (template 用 {{ xxx_json|safe }} 接收)
    sunburst_json = _json.dumps(sunburst_opt, ensure_ascii=False)
    streamgraph_json = _json.dumps(streamgraph_opt, ensure_ascii=False)
    network_json = _json.dumps(network_opt, ensure_ascii=False)
    sankey_json = _json.dumps(sankey_opt, ensure_ascii=False)

    return HTML_TEMPLATE.render(
        sunburst_json=sunburst_json,
        streamgraph_json=streamgraph_json,
        network_json=network_json,
        sankey_json=sankey_json,
        refactor_b64=refactor_bar_b64,
        module_graph_svg=module_graph_svg,
        refactor_stats=refactor_stats or {},
        build_date=build_date or date.today().isoformat(),
        translate_map_json="{}",   # Stage 2: filled by Chunk 4
        context_index_json="{}",   # Stage 2: filled by Chunk 4
    )
