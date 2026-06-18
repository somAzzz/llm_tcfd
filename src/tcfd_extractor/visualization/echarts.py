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
