"""ECharts 高级图表构建器 (Stage 1)。

4 个 builder: sunburst / streamgraph / network / sankey。
每个 builder 接受 data + theme, 返回 ECharts option dict (JSON 序列化后嵌入 HTML)。
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# 单点改动: Stage 2 视觉升级仅改此处
TCFD_THEME_CONFIG: dict[str, Any] = {
    "colors": {
        "policy": "#1f77b4",   # 政策蓝
        "market": "#ff7f0e",   # 市场橙
        "tech":   "#2ca02c",   # 技术绿
        "neutral": ["#6c757d", "#adb5bd", "#dee2e6"],
    },
    "font": "Inter, 'Helvetica Neue', -apple-system, sans-serif",
    "text_style": {"fontFamily": "Inter", "color": "#222"},
    "tooltip_style": {
        "backgroundColor": "rgba(50,50,50,0.92)",
        "borderWidth": 0,
        "textStyle": {"color": "#fff", "fontSize": 12},
    },
    "global_roam": True,
    "animation": True,
    "animation_duration": 800,
    "sankey_label_formatter": (
        "function(p) { return p.name.replace(/^stage\\d+_/, ''); }"
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
    """Sunburst: 3 维 → 聚类 → 关键词 三层树。"""
    opt = _get_base_option("TCFD 维度聚类分布", "点击节点下钻")
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
    """Streamgraph: year × 3 维 堆叠流图, dataZoom 缩放。"""
    opt = _get_base_option("TCFD 披露趋势 (2000-2024)", "拖动底部滑块缩放时间区间")
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
