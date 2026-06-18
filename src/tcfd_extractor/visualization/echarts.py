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


def build_network(data: dict, theme: dict) -> dict:
    """Force-directed 网络: 节点可拖拽, force layout。"""
    opt = _get_base_option("关键词共现网络 (近 3 年)", "可拖拽节点, hover 显示共现次数")
    n_edges = len(data["links"])
    # 边数过少时, 注入 subtext 提示
    if n_edges < 50:
        opt["title"]["subtext"] = (
            f"⚠️ 当前年份披露数据较少 (仅 {n_edges} 边), "
            "已自动降低关联阈值展示"
        )
        opt["graphic"] = [{
            "type": "text", "left": "center", "top": "middle",
            "style": {"text": f"共 {len(data['nodes'])} 节点, {n_edges} 边",
                      "fontSize": 14, "fill": "#666"},
        }]
    opt["series"] = [{
        "type": "graph",
        "layout": "force",
        "nodes": data["nodes"],
        "links": data["links"],
        "categories": [{"name": "政策"}, {"name": "市场"}, {"name": "技术"}],
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
    """Sankey: 4 阶段流水线, 节点命名空间前缀, 渲染时剥离。"""
    opt = _get_base_option("NLP 流水线数据提纯",
                          "10,814 份报告 → 分块 → 披露 → 维度归类")
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
