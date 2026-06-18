"""echarts.py 单元测试: TCFD_THEME_CONFIG + 4 builder 骨架断言。"""
from __future__ import annotations

import pytest

from tcfd_extractor.visualization.echarts import (
    TCFD_THEME_CONFIG,
    _get_base_option,
    build_sunburst,
    build_streamgraph,
    # build_network,  # Task 2.4
    # build_sankey,   # Task 2.5
)


def test_tcfd_theme_config_has_required_keys():
    """主题配置必备字段存在。"""
    required = ["colors", "font", "text_style", "tooltip_style",
                "global_roam", "animation", "animation_duration",
                "sankey_label_formatter"]
    for key in required:
        assert key in TCFD_THEME_CONFIG, f"missing key: {key}"


def test_tcfd_theme_colors_are_hex():
    """3 维颜色必须是 hex 格式。"""
    for dim in ["policy", "market", "tech"]:
        c = TCFD_THEME_CONFIG["colors"][dim]
        assert c.startswith("#") and len(c) == 7, f"{dim} color {c} not hex"


def test_tcfd_theme_sankey_formatter_strips_stage_prefix():
    """Sankey formatter 必须能剥离 stage{N}_ 前缀。"""
    fmt = TCFD_THEME_CONFIG["sankey_label_formatter"]
    assert "stage\\d+_" in fmt, "formatter must contain stage prefix regex"


def test_get_base_option_returns_skeleton():
    """_get_base_option 返回含 title/tooltip/color/textStyle 的 dict。"""
    opt = _get_base_option("测试标题", "副标题")
    assert opt["title"]["text"] == "测试标题"
    assert opt["title"]["subtext"] == "副标题"
    assert "tooltip" in opt
    assert "color" in opt
    assert "textStyle" in opt
    assert opt["textStyle"]["fontFamily"] == "Inter"


def test_build_sunburst_returns_echarts_option_skeleton():
    """Sunburst builder 输出 ECharts sunburst series。"""
    data = [
        {"name": "政策", "children": [
            {"name": "聚类A", "children": [{"name": "词1", "value": 1}]}
        ]},
        {"name": "市场", "children": []},
        {"name": "技术", "children": []},
    ]
    opt = build_sunburst(data, TCFD_THEME_CONFIG)
    assert opt["series"][0]["type"] == "sunburst"
    assert len(opt["series"][0]["data"]) == 3  # 3 个 dim 根
    assert opt["series"][0]["data"][0]["children"][0]["name"] == "聚类A"


def test_build_streamgraph_returns_stacked_line_series():
    """Streamgraph: 3 个 stack='total' 的 line series + dataZoom 控件。"""
    data = {
        "years": [2020, 2021, 2022],
        "series": [
            {"name": "政策", "data": [5, 7, 9]},
            {"name": "市场", "data": [2, 1, 3]},
            {"name": "技术", "data": [3, 4, 6]},
        ],
    }
    opt = build_streamgraph(data, TCFD_THEME_CONFIG)
    assert len(opt["series"]) == 3
    for s in opt["series"]:
        assert s["type"] == "line"
        assert s["stack"] == "total"
        assert s.get("smooth") is True
    assert "dataZoom" in opt
    assert opt["xAxis"]["data"] == [2020, 2021, 2022]
