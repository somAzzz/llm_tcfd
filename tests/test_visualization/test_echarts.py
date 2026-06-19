"""echarts.py 单元测试: TCFD_THEME_CONFIG + 4 builder 骨架断言。"""
from __future__ import annotations

import pytest

from tcfd_extractor.visualization.echarts import (
    TCFD_THEME_CONFIG,
    _get_base_option,
    _t,
    build_sunburst,
    build_streamgraph,
    build_network,
    build_sankey,
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


def test_build_network_returns_force_graph_with_unique_ids():
    """Network builder: graph + force layout, 节点 id 唯一, symbolSize 在 [10, 60]。"""
    data = {
        "nodes": [
            {"id": "词A", "name": "词A", "symbolSize": 15, "category": "政策", "value": 2},
            {"id": "词B", "name": "词B", "symbolSize": 10, "category": "市场", "value": 1},
            {"id": "词C", "name": "词C", "symbolSize": 60, "category": "政策", "value": 200},
        ],
        "links": [
            {"source": "词A", "target": "词B", "weight": 5},
            {"source": "词A", "target": "词C", "weight": 100},
        ],
    }
    opt = build_network(data, TCFD_THEME_CONFIG)
    assert opt["series"][0]["type"] == "graph"
    assert opt["series"][0]["layout"] == "force"
    assert opt["series"][0]["draggable"] is True
    node_ids = [n["id"] for n in opt["series"][0]["nodes"]]
    assert len(node_ids) == len(set(node_ids))
    for n in opt["series"][0]["nodes"]:
        assert 10 <= n["symbolSize"] <= 60
    # 边界断言: 词C 频次最高, symbolSize 应被 clamp 到上限 60
    nodes_by_id = {n["id"]: n for n in opt["series"][0]["nodes"]}
    assert nodes_by_id["词C"]["symbolSize"] == 60


def test_build_sankey_returns_sankey_with_namespace_prefix():
    """Sankey builder: type='sankey', 节点都有 stage{N}_ 前缀, formatter 剥离。"""
    data = {
        "nodes": [
            {"name": "stage1_report_万科A_2023"},
            {"name": "stage2_chunk_万科A_2023"},
            {"name": "stage3_disclosure_万科A_2023"},
            {"name": "stage4_dim_policy"},
        ],
        "links": [
            {"source": "stage1_report_万科A_2023", "target": "stage2_chunk_万科A_2023", "value": 150},
            {"source": "stage2_chunk_万科A_2023", "target": "stage3_disclosure_万科A_2023", "value": 27},
            {"source": "stage3_disclosure_万科A_2023", "target": "stage4_dim_policy", "value": 2},
        ],
    }
    opt = build_sankey(data, TCFD_THEME_CONFIG)
    assert opt["series"][0]["type"] == "sankey"
    for n in opt["series"][0]["nodes"]:
        assert n["name"].startswith("stage")
    # formatter 来自 TCFD_THEME_CONFIG
    assert "stage\\d+_" in opt["series"][0]["label"]["formatter"]


class TestTranslateHelper:
    """echarts.py _t() helper — 4 case。"""

    def test_known_keyword_returns_english(self):
        assert _t("碳交易") == "Carbon Trading"
        assert _t("政策") == "Policy"

    def test_pure_ascii_returns_as_is(self):
        assert _t("ESG") == "ESG"
        assert _t("TCFD") == "TCFD"

    def test_unknown_chinese_wrapped_double_brackets(self):
        result = _t("某未知词")
        assert result == "[[ZH: 某未知词]]"
        assert result.startswith("[[ZH:")
        assert result.endswith("]]")

    def test_empty_string_returns_empty(self):
        assert _t("") == ""


class TestDarkThemePalette:
    """Spec §6.2: 暗色调色板 policy/market/tech 用亮色调, 暗色背景下对比度足够。"""

    def test_policy_color_uses_bright_blue(self):
        # 暗色友好: 亮蓝替代 #1f77b4
        assert TCFD_THEME_CONFIG["colors"]["policy"] == "#58a6ff"

    def test_market_color_uses_bright_orange(self):
        # 暗色友好: 亮橙替代 #ff7f0e
        assert TCFD_THEME_CONFIG["colors"]["market"] == "#f0883e"

    def test_tech_color_uses_bright_green(self):
        # 暗色友好: 亮绿替代 #2ca02c
        assert TCFD_THEME_CONFIG["colors"]["tech"] == "#56d364"

    def test_palette_uses_dark_friendly_bright_colors(self):
        """Spec §6.2: 暗色背景下用亮色调 (替代 Stage 1 暗色调)."""
        assert TCFD_THEME_CONFIG["colors"]["policy"] == "#58a6ff"
        assert TCFD_THEME_CONFIG["colors"]["market"] == "#f0883e"
        assert TCFD_THEME_CONFIG["colors"]["tech"] == "#56d364"

    def test_tooltip_text_color_is_white_for_dark(self):
        # 暗色默认下 tooltip 文字白色
        assert TCFD_THEME_CONFIG["tooltip_style"]["textStyle"]["color"] == "#fff"

    def test_sankey_formatter_uses_client_translator(self):
        """Sankey formatter 走 window.__hrTranslate 客户端兜底。"""
        fmt = TCFD_THEME_CONFIG["sankey_label_formatter"]
        assert "window.__hrTranslate" in fmt
        assert "stage\\d+_" in fmt  # 仍剥离 stage{N}_ 前缀


def _has_no_cjk(s: str) -> bool:
    """Returns True iff `s` contains no CJK Unified Ideographs (U+4E00..U+9FFF).

    Used to verify English-ification: any Chinese characters anywhere in the
    string would fail this check. Non-CJK Unicode (arrows like →, emoji like
    ⚠️, Latin extended, etc.) is permitted — these are intentional design
    choices, not Chinese text.
    """
    return all(not (0x4E00 <= ord(c) <= 0x9FFF) for c in s)


class TestBuildersEnglishTitles:
    """Spec §5.3: 4 个 builder 标题/副标题全部英文化。"""

    def test_build_sunburst_title_is_english(self):
        data = [{"name": "Policy", "children": [{"name": "Cluster A", "children": []}]}]
        opt = build_sunburst(data, TCFD_THEME_CONFIG)
        title = opt["title"]["text"]
        assert "TCFD" in title  # TCFD 缩写保留
        assert _has_no_cjk(title), f"CJK in title: {title!r}"

    def test_build_streamgraph_title_is_english(self):
        data = {
            "years": [2020, 2021],
            "series": [{"name": "Policy", "data": [1, 2]}],
        }
        opt = build_streamgraph(data, TCFD_THEME_CONFIG)
        title = opt["title"]["text"]
        sub = opt["title"].get("subtext", "")
        assert _has_no_cjk(title)
        assert _has_no_cjk(sub)

    def test_build_network_title_and_categories_are_english(self):
        data = {
            "nodes": [{"id": "a", "name": "a", "symbolSize": 15, "category": "Policy", "value": 1}],
            "links": [],
        }
        opt = build_network(data, TCFD_THEME_CONFIG)
        title = opt["title"]["text"]
        sub = opt["title"].get("subtext", "")
        assert _has_no_cjk(title)
        assert _has_no_cjk(sub)
        # categories 改为英文 (Policy/Market/Technology)
        cats = opt["series"][0]["categories"]
        cat_names = [c["name"] for c in cats]
        assert "Policy" in cat_names
        assert "Market" in cat_names
        assert "Technology" in cat_names

    def test_build_sankey_title_is_english(self):
        data = {
            "nodes": [{"name": "stage1_x"}],
            "links": [],
        }
        opt = build_sankey(data, TCFD_THEME_CONFIG)
        title = opt["title"]["text"]
        sub = opt["title"].get("subtext", "")
        assert _has_no_cjk(title)
        assert _has_no_cjk(sub)
