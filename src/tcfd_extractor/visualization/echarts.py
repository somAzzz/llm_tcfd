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
    # Stage 3 修复: chart canvas 透明, 与 dark page bg (#0f1419) 融合
    "chart_background": "transparent",
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
    # Stage 3.2 修复: sankey_label_formatter 已移除 — load_sankey_data 现在
    # 直接产出 clean English 节点名 (e.g., "Reports 2023"), ECharts 用默认
    # {b} template 渲染节点名。旧实现把 JS 源码塞进 formatter 字符串, ECharts
    # 当 template 渲染, 显示 "function(p) { const t = ..." 乱码。
}


def _get_base_option(title: str, subtitle: str | None = None) -> dict:
    """返回 ECharts option 公共骨架, 注入全局 textStyle/tooltip/color/background。

    Stage 3 修复:
    - backgroundColor: "transparent" 让 chart canvas 与 dark page bg 融合

    Stage 3.3 修复: 标题块 (title + subtext) 高度固定 50px, 用 itemGap 留出
    title 和 subtext 之间的间距, 并预留 CHART_CONTENT_TOP (60px) 给上层
    builder 用 grid/series.top, 避免标题和图表内容重叠。
    """
    base: dict[str, Any] = {
        "title": {"text": title, "left": "center", "top": 10,
                  "itemGap": 4,  # title 和 subtext 之间的间距
                  "textStyle": TCFD_THEME_CONFIG["text_style"]},
        "tooltip": {"trigger": "item", **TCFD_THEME_CONFIG["tooltip_style"]},
        "color": [
            TCFD_THEME_CONFIG["colors"]["policy"],
            TCFD_THEME_CONFIG["colors"]["market"],
            TCFD_THEME_CONFIG["colors"]["tech"],
        ] + TCFD_THEME_CONFIG["colors"]["neutral"],
        "backgroundColor": TCFD_THEME_CONFIG["chart_background"],
        "textStyle": TCFD_THEME_CONFIG["text_style"],
        "animation": TCFD_THEME_CONFIG["animation"],
        "animationDuration": TCFD_THEME_CONFIG["animation_duration"],
    }
    if subtitle:
        base["title"]["subtext"] = subtitle
    return base


# Stage 3.3: 标题块 (title + subtext) 高度 ≈ 50px, 给上层 builder 参考
# Stage 3.3 调优 round 5: force-layout 节点 cluster 中心 ≈ layout 中心,
# 节点 spread 上方 ~50px (repulsion 80). 配合网络 repulsion 80→150 让
# 节点更分散, series.top 用 130 即可让最上面的节点离 subtext ≥ 25px
CHART_CONTENT_TOP = 130
CHART_CONTENT_BOTTOM = 40


# builder 函数将在 Task 2.2-2.5 添加


def build_sunburst(data: list[dict], theme: dict) -> dict:
    """Sunburst: 3 dim → cluster → keyword 3-level tree.

    Stage 3 修复: label.show=False (默认不显示), emphasis.label.show=True
    (鼠标悬停时显示英文内容)。

    Stage 3.3 修复: 设置 series.top/bottom/left/right 显式避开标题块,
    避免外圈压在标题文字上。
    """
    opt = _get_base_option(
        "TCFD Dimensions & Clusters",
        "Click a node to drill down"
    )
    opt["series"] = [{
        "type": "sunburst",
        "data": data,
        # Stage 3.3 调优: 外圈从 90% 降到 85% + 中心偏下, 避免外圈压标题
        "radius": ["10%", "85%"],
        "center": ["50%", "55%"],
        "top": CHART_CONTENT_TOP,
        "bottom": CHART_CONTENT_BOTTOM,
        "left": "5%",
        "right": "5%",
        "label": {"show": False, "rotate": "tangential", "fontSize": 11,
                  "color": theme["text_style"]["color"]},
        "emphasis": {
            "focus": "ancestor",
            "label": {"show": True, "rotate": "tangential", "fontSize": 12,
                      "color": "#fff"},
        },
        "nodeClick": "zoomToNode",
        "sort": None,
        "animation": theme["animation"],
        "animationDuration": theme["animation_duration"],
    }]
    return opt


def build_streamgraph(data: dict, theme: dict) -> dict:
    """Streamgraph: year × 3 dim stacked flow, dataZoom for zoom.

    Stage 3 修复: 每个 series label.show=False, emphasis 时显示 dim 名称。

    Stage 3.3 修复:
    - legend 移到 top:55 (在标题块下沿, 不与 subtext 重叠)
    - grid.top 设为 90 (legend 下 + 留白), 避免曲线压在 legend/subtext 上
    - grid.bottom 设 50 留给 dataZoom slider
    """
    opt = _get_base_option(
        "TCFD Disclosure Trend (2000-2024)",
        "Drag the slider to zoom into a time range"
    )
    # legend name 已经从 data["series"] 拿, 由 data_loader 翻译
    # Stage 3.3 round 5: legend top = 105 (与 CHART_CONTENT_TOP=130 协调)
    opt["legend"] = {"top": 105, "data": [s["name"] for s in data["series"]]}
    opt["xAxis"] = {"type": "category", "boundaryGap": False,
                    "data": data["years"]}
    opt["yAxis"] = {"type": "value"}
    # Stage 3.3 round 5: grid.top=140 给 legend 下沿留 15px, bottom=65 给
    # dataZoom slider 留空间
    opt["grid"] = {"top": 140, "left": 60, "right": 30, "bottom": 65,
                   "containLabel": True}
    opt["dataZoom"] = [
        {"type": "slider", "xAxisIndex": 0, "start": 0, "end": 100,
         "bottom": 10},
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
            "label": {"show": False},
            "emphasis": {
                "focus": "series",
                "label": {"show": True, "color": "#fff", "fontSize": 12},
            },
        })
    return opt


def build_network(data: dict, theme: dict) -> dict:
    """Force-directed network: draggable nodes, force layout.

    Stage 3 修复: label.show=False (默认不显示), emphasis.label.show=True
    (悬停节点时显示关键词名)。

    Stage 3.3 修复: 显式设置 series.top/bottom/left/right, force-layout
    节点限制在标题块下方, 避免最上面的节点压在 title/subtext 上。
    """
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
        # Stage 3.3: 限制绘图区在标题块下方
        "top": CHART_CONTENT_TOP,
        "bottom": CHART_CONTENT_BOTTOM,
        "left": 20,
        "right": 20,
        # Stage 3.3 round 5: repulsion 80→150 让节点更分散, 避免 cluster
        # 顶部节点压到 subtext/标题
        "force": {"repulsion": 150, "edgeLength": 50},
        "emphasis": {
            "focus": "adjacency",
            "label": {"show": True, "position": "right", "fontSize": 11,
                      "color": "#fff"},
        },
        "lineStyle": {"curveness": 0.1, "width": 1},
        "label": {"show": False, "position": "right", "fontSize": 10},
        "animation": theme["animation"],
        "animationDuration": theme["animation_duration"],
    }]
    return opt


def build_sankey(data: dict, theme: dict) -> dict:
    """Sankey: 4-stage pipeline, clean English node names.

    Stage 3 修复: 节点 label (label) + 边 label (edgeLabel) 都默认隐藏,
    鼠标悬停时 ECharts 通过 emphasis 自动显示。

    Stage 3.2 修复: 不再用 formatter (旧实现把 JS 源码塞进 formatter 字符串,
    ECharts 当 template 渲染, 显示 "function(p) { const t = ..." 乱码)。
    节点名已经是 clean English ("Reports 2023" 等), ECharts 用默认 {b}
    template 直接显示节点名。

    Stage 3.3 修复: top 从 60 微调到 70 (与 CHART_CONTENT_TOP 对齐),
    保证标题块和图表内容不重叠。
    """
    opt = _get_base_option(
        "NLP Pipeline Data Refinement",
        "10,814 reports → chunking → disclosure → by dimension"
    )
    opt["series"] = [{
        "type": "sankey",
        "nodes": data["nodes"],
        "links": data["links"],
        "emphasis": {
            "focus": "adjacency",
            "label": {"show": True, "fontSize": 12, "color": "#fff"},
            "edgeLabel": {"show": True, "fontSize": 11, "color": "#e6e6e6"},
        },
        "lineStyle": {"color": "gradient", "curveness": 0.5},
        "label": {
            "show": False,
            "fontSize": 11,
        },
        # 边 (link) 上的 label — 默认隐藏, 悬停显示
        "edgeLabel": {
            "show": False,
            "fontSize": 10,
        },
        "left": 20, "right": 100,
        "top": CHART_CONTENT_TOP, "bottom": CHART_CONTENT_BOTTOM,
    }]
    return opt
