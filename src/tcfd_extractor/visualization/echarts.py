"""ECharts 高级图表构建器 (Stage 1)。

4 个 builder: sunburst / streamgraph / network / sankey。
每个 builder 接受 data + theme, 返回 ECharts option dict (JSON 序列化后嵌入 HTML)。
"""
from __future__ import annotations

import logging
from typing import Any

from .translations import translate_smart

logger = logging.getLogger(__name__)


def _t(keyword: str) -> str:
    """echarts.py 内部统一翻译 helper — 走 translate_smart()。"""
    return translate_smart(keyword)


# 单点改动: Stage 2 视觉升级仅改此处
TCFD_THEME_CONFIG: dict[str, Any] = {
    "colors": {
        "policy": "#58a6ff",   # 暗色下用亮蓝 (替代 #1f77b4)
        "market": "#f0883e",   # 暗色下用亮橙 (替代 #ff7f0e)
        "tech":   "#56d364",   # 暗色下用亮绿 (替代 #2ca02c)
        "neutral": ["#8b95a1", "#6c757d", "#484f58"],
    },
    "font": "Inter, 'Helvetica Neue', -apple-system, sans-serif",
    "text_style": {"fontFamily": "Inter", "color": "#e6e6e6"},  # 暗色默认
    "tooltip_style": {
        "backgroundColor": "rgba(20,20,20,0.95)",
        "borderWidth": 1,
        "borderColor": "rgba(255,255,255,0.1)",
        "textStyle": {"color": "#fff", "fontSize": 12, "fontFamily": "Inter"},
    },
    "global_roam": True,
    "animation": True,
    "animation_duration": 600,
    "sankey_label_formatter": (
        "function(p) {"
        "  const t = window.__hrTranslate || (s => s);"
        "  return t(p.name.replace(/^stage\\d+_/, ''));"
        "}"
    ),
}


def _get_base_option(title: str, subtitle: str | None = None) -> dict:
    """返回 ECharts option 公共骨架, 注入全局 textStyle/tooltip/color。"""
    base: dict[str, Any] = {
        "title": {"text": title, "left": "center", "top": 10,
                  "textStyle": TCFD_THEME_CONFIG["text_style"]},
        "tooltip": {"trigger": "item", **TCFD_THEME_CONFIG["tooltip_style"]},
        "color": [
            TCFD_THEME_CONFIG["colors"]["policy"],
            TCFD_THEME_CONFIG["colors"]["market"],
            TCFD_THEME_CONFIG["colors"]["tech"],
        ] + TCFD_THEME_CONFIG["colors"]["neutral"],
        "textStyle": TCFD_THEME_CONFIG["text_style"],
        "animation": TCFD_THEME_CONFIG["animation"],
        "animationDuration": TCFD_THEME_CONFIG["animation_duration"],
    }
    if subtitle:
        base["title"]["subtext"] = subtitle
    return base


# builder 函数将在 Task 2.2-2.5 添加


def build_sunburst(data: list[dict], theme: dict) -> dict:
    """Sunburst: 3 dim → cluster → keyword 3-level tree."""
    opt = _get_base_option(
        "TCFD Dimensions & Clusters",
        "Click a node to drill down"
    )
    opt["series"] = [{
        "type": "sunburst",
        "data": data,
        "radius": ["10%", "90%"],
        "label": {"rotate": "tangential", "fontSize": 11,
                  "color": theme["text_style"]["color"]},
        "emphasis": {"focus": "ancestor"},
        "nodeClick": "zoomToNode",
        "sort": None,
        "animation": theme["animation"],
        "animationDuration": theme["animation_duration"],
    }]
    return opt


def build_streamgraph(data: dict, theme: dict) -> dict:
    """Streamgraph: year × 3 dim stacked flow, dataZoom for zoom."""
    opt = _get_base_option(
        "TCFD Disclosure Trend (2000-2024)",
        "Drag the slider to zoom into a time range"
    )
    # legend name 已经从 data["series"] 拿, 由 data_loader 翻译
    opt["legend"] = {"top": 30, "data": [s["name"] for s in data["series"]]}
    opt["xAxis"] = {"type": "category", "boundaryGap": False,
                    "data": data["years"]}
    opt["yAxis"] = {"type": "value"}
    opt["dataZoom"] = [
        {"type": "slider", "xAxisIndex": 0, "start": 0, "end": 100},
        {"type": "inside", "xAxisIndex": 0},
    ]
    opt["series"] = []
    for s in data["series"]:
        opt["series"].append({
            "name": s["name"],
            "type": "line",
            "stack": "total",
            "smooth": True,
            "data": s["data"],
            "areaStyle": {"opacity": 0.7},
            "emphasis": {"focus": "series"},
        })
    return opt


def build_network(data: dict, theme: dict) -> dict:
    """Force-directed network: draggable nodes, force layout."""
    opt = _get_base_option(
        "Keyword Co-occurrence Network (Recent 3 Years)",
        "Draggable nodes, hover to see co-occurrence count"
    )
    n_edges = len(data["links"])
    # 边数过少时, 注入 subtext 提示
    if n_edges < 50:
        opt["title"]["subtext"] = (
            f"⚠️ Limited data this period (only {n_edges} edges), "
            "threshold lowered to show more"
        )
        opt["graphic"] = [{
            "type": "text", "left": "center", "top": "middle",
            "style": {"text": f"{len(data['nodes'])} nodes, {n_edges} edges",
                      "fontSize": 14, "fill": "#666"},
        }]
    opt["series"] = [{
        "type": "graph",
        "layout": "force",
        "nodes": data["nodes"],
        "links": data["links"],
        # Categories 改为英文 (与 __hrTranslate 一致, 客户端兜底)
        "categories": [
            {"name": "Policy"},
            {"name": "Market"},
            {"name": "Technology"},
        ],
        "roam": theme["global_roam"],
        "draggable": True,
        "force": {"repulsion": 80, "edgeLength": 50},
        "emphasis": {"focus": "adjacency"},
        "lineStyle": {"curveness": 0.1, "width": 1},
        "label": {"show": True, "position": "right", "fontSize": 10},
        "animation": theme["animation"],
        "animationDuration": theme["animation_duration"],
    }]
    return opt


def build_sankey(data: dict, theme: dict) -> dict:
    """Sankey: 4-stage pipeline, namespace prefix on nodes."""
    opt = _get_base_option(
        "NLP Pipeline Data Refinement",
        "10,814 reports → chunking → disclosure → by dimension"
    )
    opt["series"] = [{
        "type": "sankey",
        "nodes": data["nodes"],
        "links": data["links"],
        "emphasis": {"focus": "adjacency"},
        "lineStyle": {"color": "gradient", "curveness": 0.5},
        "label": {
            "formatter": theme["sankey_label_formatter"],
            "fontSize": 11,
        },
        "left": 20, "right": 100, "top": 60, "bottom": 20,
    }]
    return opt
