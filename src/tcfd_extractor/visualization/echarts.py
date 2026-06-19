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
        # Stage 4 round 3 调亮: dim 层半径占比 5%→12% 后, 这 3 色作为最内圈
        # 直接对眼睛, 需要比 cluster 环 (alpha=0.4) 和外圈 (深蓝) 都更亮更饱和
        # 用户反馈: "最内层的 tech, policy, market 颜色有点暗"
        "policy": "#79c0ff",   # Stage 4 r3: #58a6ff → #79c0ff (更亮的天蓝)
        "market": "#ffa657",   # Stage 4 r3: #f0883e → #ffa657 (更亮的琥珀)
        "tech":   "#7ee787",   # Stage 4 r3: #56d364 → #7ee787 (更亮的嫩绿)
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


# JS formatter source strings for build_pipeline_health_dashboard.
# Receives `params.data.metric` and returns a formatted string.
_LABEL_FN = (
    "function (params) {"
    "  var m = params.data && params.data.metric;"
    "  if (!m) return String(params.value);"
    "  var v = (m.unit === 'tests') ? Math.round(params.value) : params.value;"
    "  return v + ' ' + m.unit;"
    "}"
)

_PIPELINE_HEALTH_TOOLTIP_FN = (
    "function (params) {"
    "  return params.map(function (p) {"
    "    var m = p.data && p.data.metric;"
    "    if (!m) return p.seriesName + ': ' + p.value;"
    "    return p.seriesName + ' \u00b7 ' + p.name + '<br/>'"
    "      + '<b>' + p.value + ' ' + m.unit + '</b><br/>'"
    "      + '<span style=\"color:#8b949e;font-size:11px\">' + m.note + '</span>';"
    "  }).join('<hr/>');"
    "}"
)

_WRAP_XAXIS_FN = (
    "function (value) {"
    "  if (value.length <= 14) return value;"
    "  var words = value.split(' ');"
    "  var line = '', lines = [];"
    "  for (var i = 0; i < words.length; i++) {"
    "    if ((line + ' ' + words[i]).trim().length > 14) {"
    "      lines.push(line.trim()); line = words[i];"
    "    } else { line = line + ' ' + words[i]; }"
    "  }"
    "  if (line) lines.push(line.trim());"
    "  return lines.join('\\n');"
    "}"
)


# builder 函数将在 Task 2.2-2.5 添加


def build_sunburst(data: list[dict], theme: dict) -> dict:
    """Sunburst: 3 dim → cluster → keyword 3-level tree.

    Stage 3 修复: label.show=False (默认不显示), emphasis.label.show=True
    (鼠标悬停时显示英文内容)。

    Stage 3.3 修复: 设置 series.top/bottom/left/right 显式避开标题块,
    避免外圈压在标题文字上。

    Stage 4 修复: 加 levels 配置, 最外圈 (keyword 层级) 用深蓝色 #0a1929,
    替代默认白/浅色 (用户反馈 "把sunburst的最下面那层改成深蓝色")。
    levels 按 depth 索引: levels[1]=dim, levels[2]=cluster, levels[3]=keyword。

    Stage 4 颜色继承增强: levels[2] (cluster) 不再写死灰色, 而是依赖
    load_sunburst_data 给每个 cluster 节点注入的 itemStyle.color (父辈 dim
    颜色的 alpha=0.4 rgba)。这样 cluster 层视觉上是 "父辈 dim 色的淡化
    过渡", 实现 亮色 → 半透明过渡 → 深蓝 的色彩渐进流动。

    Stage 4 emphasis 增强: levels[3] (keyword/最外圈) 加 shadowBlur +
    shadowColor, 鼠标悬停时发淡白光, 抵抗炭黑背景 (#0f1419) 让深蓝环
    不至于看不清。
    """
    opt = _get_base_option(
        "TCFD Dimensions & Clusters",
        "Click a node to drill down"
    )
    # Stage 4: 3 个 dim 颜色用作 dim 层 (depth=1) 的 itemStyle.color list
    dim_colors = [
        theme["colors"]["policy"],
        theme["colors"]["market"],
        theme["colors"]["tech"],
    ]
    opt["series"] = [{
        "type": "sunburst",
        "data": data,
        # Stage 4 round 3 调优: 最内圈 (dim 层) 半径 10% → 15%, 让 Policy/Market/Technology
        # 3 色的视觉占比更大, 不再被压成窄环显得暗淡。cluster/keyword 层相应被压窄
        # (从 75% 总宽 → 70%), 但 3 层仍然清晰可分。
        "radius": ["15%", "85%"],
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
        # Stage 4: 按深度控制每层颜色
        # levels[0] 兜底 (无节点), levels[1]=dim, levels[2]=cluster, levels[3]=keyword
        "levels": [
            {},  # 0: 兜底
            {  # 1: dim (Policy/Market/Technology) - 亮色
                "itemStyle": {"color": dim_colors},
            },
            {},  # 2: cluster - 颜色由 load_sunburst_data 注入的 per-node
                 # itemStyle.color 决定 (父辈 dim 色 alpha=0.4 rgba), ECharts
                 # 优先 per-node, 这里留空避免覆盖
            {  # 3: keyword (最外圈) - 深蓝色 + 边框 + 悬停发光
                "itemStyle": {"color": "#0a1929", "borderColor": "#1f3a5a",
                              "borderWidth": 1},
                # 悬停时发淡白光抵抗炭黑背景, 同时自动高亮 ancestor 链
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowColor": "rgba(255, 255, 255, 0.1)",
                    },
                },
            },
        ],
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
        # Stage 3.3 round 6: 网络额外加 20px top 缓冲, 防止 force-layout
        # 软约束边界节点擦标题
        "top": CHART_CONTENT_TOP + 20,
        "bottom": CHART_CONTENT_BOTTOM,
        "left": 20,
        "right": 20,
        # Stage 3.3 round 5: repulsion 80→150 让节点更分散, 避免 cluster
        # 顶部节点压到 subtext/标题
        # Stage 3.3 round 6: gravity 0.1 让节点向 center 拉, 减少越界
        "force": {"repulsion": 150, "edgeLength": 50, "gravity": 0.1},
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


def build_pipeline_health_dashboard(
    metrics: list["PipelineMetric"],
    theme: dict,
) -> dict:
    """Build the AI Pipeline Resilience & Engineering Health ECharts option.

    Each metric becomes a grouped bar pair (Before / After).
    Y-axis is hidden; per-bar label shows formatted value with unit.
    Inherits `_get_base_option()` styling (chart background, text style,
    animation) so the dashboard participates in the `applyTheme()` cycle
    used by the other 4 ECharts dashboards in the report.
    """
    from tcfd_extractor.visualization.pipeline_metrics import PipelineMetric

    metrics = list(metrics)  # accept any iterable
    bar_labels = [m.name for m in metrics]
    before_vals = [m.before for m in metrics]
    after_vals = [m.after for m in metrics]

    opt = _get_base_option(
        "AI Pipeline Resilience & Engineering Health",
        "Click any bar to view the module graph",
    )
    opt["title"]["left"] = "center"
    opt["title"]["textStyle"] = {
        **theme.get("text_style", {}),
        "fontWeight": 600,
        "fontSize": 16,
    }
    opt["tooltip"] = {
        "trigger": "axis",
        "axisPointer": {"type": "shadow"},
        "formatter": _PIPELINE_HEALTH_TOOLTIP_FN,
    }
    opt["legend"] = {
        "data": ["Before (god-class)", "After (refactored)"],
        "top": 32,
        "textStyle": theme.get("text_style", {}),
    }
    opt["grid"] = {"left": 50, "right": 30, "top": 80, "bottom": 50}
    opt["xAxis"] = {
        "type": "category",
        "data": bar_labels,
        "axisLabel": {
            "color": theme.get("text_style", {}).get("color", "#c9d1d9"),
            "interval": 0,
            "fontSize": 11,
            "formatter": _WRAP_XAXIS_FN,
        },
    }
    opt["yAxis"] = {"type": "value", "show": False}
    opt["color"] = ["#8b3a3a", "#56d364"]
    opt["series"] = [
        {
            "name": "Before (god-class)",
            "type": "bar",
            "data": [
                {"value": v, "metric": m} for v, m in zip(before_vals, metrics)
            ],
            "label": {
                "show": True,
                "position": "top",
                "color": theme.get("text_style", {}).get("color", "#c9d1d9"),
                "formatter": _LABEL_FN,
            },
            "emphasis": {"focus": "series"},
        },
        {
            "name": "After (refactored)",
            "type": "bar",
            "data": [
                {"value": v, "metric": m} for v, m in zip(after_vals, metrics)
            ],
            "label": {
                "show": True,
                "position": "top",
                "color": theme.get("colors", {}).get("tech", "#56d364"),
                "formatter": _LABEL_FN,
            },
            "emphasis": {"focus": "series"},
        },
    ]
    return opt


def build_module_graph(
    graph: dict[str, list[str]],
    theme: dict,
) -> dict:
    """Build a force-directed graph ECharts option from a module→deps mapping.

    `graph` shape: `{"config": [], "evaluator": ["config"], ...}` —
    returned by `discover_module_graph()` in `module_graph.py`.

    Empty dict → empty graph (caller must handle this with try/except).
    """
    nodes = [{"id": name, "name": name, "category": 0} for name in graph]
    links = [
        {"source": src, "target": tgt}
        for src, deps in graph.items()
        for tgt in deps
    ]
    opt = _get_base_option(
        "Module Dependency Graph",
        "Hover a module to highlight its dependencies",
    )
    opt["title"]["left"] = "center"
    opt["tooltip"] = {"formatter": "{b}"}
    opt["series"] = [
        {
            "type": "graph",
            "layout": "force",
            "data": nodes,
            "links": links,
            "force": {"repulsion": 200, "edgeLength": 80},
            "emphasis": {"focus": "adjacency", "lineStyle": {"width": 3}},
            "label": {"show": True, "position": "right", "fontSize": 12},
            "lineStyle": {"color": "source", "curveness": 0.1, "opacity": 0.6},
        }
    ]
    return opt
