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
                "chart_background"]
    for key in required:
        assert key in TCFD_THEME_CONFIG, f"missing key: {key}"


def test_tcfd_theme_colors_are_hex():
    """3 维颜色必须是 hex 格式。"""
    for dim in ["policy", "market", "tech"]:
        c = TCFD_THEME_CONFIG["colors"][dim]
        assert c.startswith("#") and len(c) == 7, f"{dim} color {c} not hex"


def test_tcfd_theme_no_sankey_formatter_field():
    """Stage 3.2 修复: sankey_label_formatter 已移除 — 用 clean English 节点名 + 默认 {b}。

    旧实现把 JS 源码塞进 formatter 字符串, ECharts 把它当 template 渲染,
    显示 "function(p) { const t = ..." 这种乱码。
    """
    assert "sankey_label_formatter" not in TCFD_THEME_CONFIG, (
        "sankey_label_formatter should be removed; use clean English node names + default {b}"
    )


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
        {"name": "Policy", "children": [
            {"name": "Cluster A", "children": [{"name": "词1", "value": 1}]}
        ]},
        {"name": "Market", "children": []},
        {"name": "Technology", "children": []},
    ]
    opt = build_sunburst(data, TCFD_THEME_CONFIG)
    assert opt["series"][0]["type"] == "sunburst"
    assert len(opt["series"][0]["data"]) == 3  # 3 个 dim 根
    assert opt["series"][0]["data"][0]["children"][0]["name"] == "Cluster A"


def test_build_streamgraph_returns_stacked_line_series():
    """Streamgraph: 3 个 stack='total' 的 line series + dataZoom 控件。"""
    data = {
        "years": [2020, 2021, 2022],
        "series": [
            {"name": "Policy", "data": [5, 7, 9]},
            {"name": "Market", "data": [2, 1, 3]},
            {"name": "Technology", "data": [3, 4, 6]},
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


def test_build_sankey_returns_sankey_with_clean_english_names():
    """Sankey builder: type='sankey', 节点是 clean English 名 (无 stage{N}_ 前缀)。

    Stage 3.2 修复: 节点名直接是 "Reports 2023" 等 clean English, ECharts 用
    默认 {b} template 直接显示节点名 — 不再用 JS string formatter (旧实现
    把 JS 源码塞进 formatter 字符串, ECharts 当 template 渲染出乱码)。
    """
    data = {
        "nodes": [
            {"name": "Reports 2023"},
            {"name": "Chunks 2023"},
            {"name": "Disclosures 2023"},
            {"name": "Policy Keywords"},
        ],
        "links": [
            {"source": "Reports 2023", "target": "Chunks 2023", "value": 150},
            {"source": "Chunks 2023", "target": "Disclosures 2023", "value": 27},
            {"source": "Disclosures 2023", "target": "Policy Keywords", "value": 2},
        ],
    }
    opt = build_sankey(data, TCFD_THEME_CONFIG)
    assert opt["series"][0]["type"] == "sankey"
    for n in opt["series"][0]["nodes"]:
        assert not n["name"].startswith("stage"), (
            f"node {n['name']} still uses stage prefix — should be clean English"
        )
    # 无 formatter 字段 (用 ECharts 默认 {b} template)
    assert "formatter" not in opt["series"][0]["label"]
    assert "formatter" not in opt["series"][0]["edgeLabel"]


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
    """Spec §6.2: 暗色调色板 policy/market/tech 用亮色调, 暗色背景下对比度足够。

    Stage 4 round 3 调亮: 用户反馈 "最内层的 tech, policy, market 颜色有点暗",
    dim 圈 (level 1) 半径从 10% 扩到 15% 后, 这 3 色直接对眼睛, 需要更亮。
    旧值 (#58a6ff / #f0883e / #56d364) → 新值 (#79c0ff / #ffa657 / #7ee787),
    与 GitHub Primer 调色板的 accent 亮色对齐, RGB 通道整体 +30~40。
    """

    def test_policy_color_uses_bright_blue(self):
        # 暗色友好: 亮蓝替代 #1f77b4, Stage 4 r3 又调亮
        assert TCFD_THEME_CONFIG["colors"]["policy"] == "#79c0ff"

    def test_market_color_uses_bright_orange(self):
        # 暗色友好: 亮橙替代 #ff7f0e, Stage 4 r3 又调亮
        assert TCFD_THEME_CONFIG["colors"]["market"] == "#ffa657"

    def test_tech_color_uses_bright_green(self):
        # 暗色友好: 亮绿替代 #2ca02c, Stage 4 r3 又调亮
        assert TCFD_THEME_CONFIG["colors"]["tech"] == "#7ee787"

    def test_palette_uses_dark_friendly_bright_colors(self):
        """Spec §6.2 + Stage 4 r3: 暗色背景下用更亮色调, 让最内圈显眼。"""
        assert TCFD_THEME_CONFIG["colors"]["policy"] == "#79c0ff"
        assert TCFD_THEME_CONFIG["colors"]["market"] == "#ffa657"
        assert TCFD_THEME_CONFIG["colors"]["tech"] == "#7ee787"

    def test_tooltip_text_color_is_white_for_dark(self):
        # 暗色默认下 tooltip 文字白色
        assert TCFD_THEME_CONFIG["tooltip_style"]["textStyle"]["color"] == "#fff"


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


class TestLabelsHiddenByDefault:
    """Stage 3 修复: 图表默认不显示文字, 只有鼠标悬停才显示英文内容。

    4 个 chart 都必须:
    - series.label.show == False (默认)
    - series.emphasis.label.show == True (悬停时显示)
    """

    def test_sunburst_label_hidden_by_default(self):
        data = [{"name": "Policy", "children": [{"name": "A", "children": []}]}]
        opt = build_sunburst(data, TCFD_THEME_CONFIG)
        series = opt["series"][0]
        assert series["label"].get("show") is False, "sunburst label.show must be False"
        # emphasis 时显示
        assert "emphasis" in series
        assert series["emphasis"].get("label", {}).get("show") is True

    def test_streamgraph_series_label_hidden_by_default(self):
        data = {"years": [2020], "series": [{"name": "Policy", "data": [1]}]}
        opt = build_streamgraph(data, TCFD_THEME_CONFIG)
        for s in opt["series"]:
            assert s.get("label", {}).get("show") is False, \
                f"streamgraph series {s['name']} label.show must be False"

    def test_network_label_hidden_by_default(self):
        data = {
            "nodes": [{"id": "a", "name": "a", "symbolSize": 15, "category": "Policy", "value": 1}],
            "links": [],
        }
        opt = build_network(data, TCFD_THEME_CONFIG)
        series = opt["series"][0]
        assert series["label"].get("show") is False, "network label.show must be False"
        # emphasis 时显示
        assert "emphasis" in series
        assert series["emphasis"].get("label", {}).get("show") is True

    def test_sankey_label_hidden_by_default(self):
        data = {"nodes": [{"name": "stage1_x"}], "links": []}
        opt = build_sankey(data, TCFD_THEME_CONFIG)
        series = opt["series"][0]
        assert series["label"].get("show") is False, "sankey label.show must be False"
        # Stage 3.1 修复: edgeLabel 也必须默认隐藏 (避免边上数字常年显示)
        assert series.get("edgeLabel", {}).get("show") is False, \
            "sankey edgeLabel.show must be False"
        # emphasis 时显示
        assert series["emphasis"].get("edgeLabel", {}).get("show") is True, \
            "sankey emphasis.edgeLabel.show must be True (hover reveals edge label)"


class TestChartBackgroundMatchesDark:
    """Stage 3 修复: dark 背景下 chart 颜色应与 dark 背景匹配。

    ECharts 公共 base option 必须含 chart background = transparent (与 page bg 融合),
    不能用默认的 white。
    """

    def test_base_option_background_is_transparent(self):
        """_get_base_option 应注入 backgroundColor: 'transparent' 让 chart 透明。"""
        opt = _get_base_option("T", "S")
        assert opt.get("backgroundColor") == "transparent", \
            f"chart background must be transparent for dark mode, got {opt.get('backgroundColor')!r}"

    def test_theme_has_background_config(self):
        """TCFD_THEME_CONFIG 应含 chart_background 字段供 builder 使用。"""
        assert "chart_background" in TCFD_THEME_CONFIG
        assert TCFD_THEME_CONFIG["chart_background"] == "transparent"

    def test_palette_uses_dark_friendly_bright_colors(self):
        """暗色背景下 3 维颜色用亮色 (policy/market/tech), 保持 Stage 2 调色板。
        Stage 4 r3: 又调亮一档 (#79c0ff / #ffa657 / #7ee787) 让最内圈显眼。
        """
        assert TCFD_THEME_CONFIG["colors"]["policy"] == "#79c0ff"
        assert TCFD_THEME_CONFIG["colors"]["market"] == "#ffa657"
        assert TCFD_THEME_CONFIG["colors"]["tech"] == "#7ee787"


class TestTitleDoesNotOverlapChartContent:
    """Stage 3.3 修复: 4 个 chart 都必须保证标题块 (title + subtext) 不与
    图表内容 (series/grid) 重叠。

    标题块默认高度 ≈ 50px (title.top=10 + title 文字 ~18px + itemGap=4 +
    subtext ~16px = ~48px), 所以 series.top 必须 ≥ 60px 才有视觉余量。
    """

    def test_title_block_height_is_respected_by_all_builders(self):
        """所有 builder 的 series/grid.top 必须 ≥ 60, 避免与标题块重叠。"""
        # Sunburst
        data_sb = [{"name": "Policy", "children": [{"name": "A", "children": []}]}]
        opt = build_sunburst(data_sb, TCFD_THEME_CONFIG)
        assert opt["series"][0]["top"] >= 60, \
            f"sunburst series.top={opt['series'][0]['top']} < 60, will overlap title"

        # Streamgraph — 通过 grid.top 留空
        data_sg = {"years": [2020], "series": [{"name": "Policy", "data": [1]}]}
        opt = build_streamgraph(data_sg, TCFD_THEME_CONFIG)
        assert opt["grid"]["top"] >= 60, \
            f"streamgraph grid.top={opt['grid']['top']} < 60, will overlap title/legend"
        # legend 必须在标题块下方
        assert opt["legend"]["top"] >= 50, \
            f"streamgraph legend.top={opt['legend']['top']} < 50, will overlap title block"

        # Network — series.top
        data_nw = {
            "nodes": [{"id": "a", "name": "a", "symbolSize": 15, "category": "Policy", "value": 1}],
            "links": [],
        }
        opt = build_network(data_nw, TCFD_THEME_CONFIG)
        assert opt["series"][0]["top"] >= 60, \
            f"network series.top={opt['series'][0]['top']} < 60, will overlap title"

        # Sankey — series.top
        data_sk = {"nodes": [{"name": "Reports 2023"}], "links": []}
        opt = build_sankey(data_sk, TCFD_THEME_CONFIG)
        assert opt["series"][0]["top"] >= 60, \
            f"sankey series.top={opt['series'][0]['top']} < 60, will overlap title"

    def test_base_option_title_itemGap_creates_spacing(self):
        """title.itemGap 必须 > 0 让 title 和 subtext 之间有视觉间距。"""
        opt = _get_base_option("T", "S")
        assert opt["title"].get("itemGap", 0) > 0, \
            "title.itemGap must be > 0 to separate title from subtext"

    def test_streamgraph_legend_under_title_block(self):
        """Streamgraph legend 必须在 subtext 下方 (top ≥ 50)。"""
        data = {"years": [2020, 2021], "series": [
            {"name": "Policy", "data": [1, 2]},
            {"name": "Market", "data": [2, 3]},
        ]}
        opt = build_streamgraph(data, TCFD_THEME_CONFIG)
        # title 块 (含 subtext) 高度 ≈ 50, legend 应在 ≥ 50 (留余量 ≥ 55)
        assert opt["legend"]["top"] >= 55

    def test_network_series_has_explicit_bounds(self):
        """Network: force-layout 节点必须限制在标题块下方, 否则最上面的
        节点会压在 title/subtext 上 (实际部署中曾发生)。
        """
        data = {
            "nodes": [{"id": "a", "name": "a", "symbolSize": 15, "category": "Policy", "value": 1}],
            "links": [],
        }
        opt = build_network(data, TCFD_THEME_CONFIG)
        series = opt["series"][0]
        for key in ("top", "bottom", "left", "right"):
            assert key in series, f"network series missing explicit {key} bound (will overlap title)"
        assert series["top"] >= 60

    def test_sunburst_center_offset_below_title(self):
        """Sunburst: 中心 y 必须略偏下 (center[1] > 50%), 视觉上不被标题压。"""
        data = [{"name": "Policy", "children": [{"name": "A", "children": []}]}]
        opt = build_sunburst(data, TCFD_THEME_CONFIG)
        center_y_pct = int(opt["series"][0]["center"][1].rstrip("%"))
        assert center_y_pct >= 50, \
            f"sunburst center y={center_y_pct}% should be >= 50% (lower) for title clearance"

    def test_sankey_top_matches_other_charts(self):
        """Sankey series.top 应该和 sunburst/network 一致, 都用 CHART_CONTENT_TOP=130。"""
        opt = build_sankey({"nodes": [{"name": "x"}], "links": []}, TCFD_THEME_CONFIG)
        # Stage 3.3 round 5: top = 130 给 force-layout 节点最终的安全余量
        assert opt["series"][0]["top"] == 130

    def test_network_repulsion_increased_to_spread_nodes(self):
        """Stage 3.3 round 5: repulsion 80→150, 节点更分散避免压标题。"""
        data = {
            "nodes": [{"id": "a", "name": "a", "symbolSize": 15, "category": "Policy", "value": 1}],
            "links": [],
        }
        opt = build_network(data, TCFD_THEME_CONFIG)
        assert opt["series"][0]["force"]["repulsion"] >= 120, (
            f"network repulsion={opt['series'][0]['force']['repulsion']} too low, "
            "top nodes will overlap title"
        )

    def test_network_has_extra_top_buffer_above_chrome_chart(self):
        """Stage 3.3 round 6: 网络 series.top 比 chrome chart (sankey) 多 20px,
        防止 force-layout 软约束导致顶部节点擦标题。
        """
        data = {
            "nodes": [{"id": "a", "name": "a", "symbolSize": 15, "category": "Policy", "value": 1}],
            "links": [],
        }
        opt_nw = build_network(data, TCFD_THEME_CONFIG)
        opt_sk = build_sankey({"nodes": [{"name": "x"}], "links": []}, TCFD_THEME_CONFIG)
        assert opt_nw["series"][0]["top"] > opt_sk["series"][0]["top"], (
            f"network top={opt_nw['series'][0]['top']} should be > "
            f"sankey top={opt_sk['series'][0]['top']} (force-layout needs extra buffer)"
        )

    def test_sunburst_radius_reduced_to_avoid_title_overlap(self):
        """Sunburst 外圈半径 ≤ 85%, 避免外圈边缘压到 subtext。"""
        data = [{"name": "Policy", "children": [{"name": "A", "children": []}]}]
        opt = build_sunburst(data, TCFD_THEME_CONFIG)
        radius_str = opt["series"][0]["radius"][1]
        radius_pct = int(radius_str.rstrip("%"))
        assert radius_pct <= 85, (
            f"sunburst outer radius={radius_pct}% > 85%, outer ring will overlap title"
        )

    def test_streamgraph_grid_top_keeps_clearance_below_legend(self):
        """Streamgraph grid.top 必须 > legend.top + 20, 避免曲线压到 legend。"""
        data = {"years": [2020], "series": [{"name": "Policy", "data": [1]}]}
        opt = build_streamgraph(data, TCFD_THEME_CONFIG)
        assert opt["grid"]["top"] >= opt["legend"]["top"] + 25, (
            f"grid.top={opt['grid']['top']} not enough below legend.top="
            f"{opt['legend']['top']}; chart may overlap legend"
        )


class TestSunburstOutermostRingDarkBlue:
    """Stage 4 修复: sunburst 最外圈 (keyword 层级) 改成深蓝色, 而不是默认白/浅色。

    用户反馈: "把sunburst的最下面那层改成深蓝色, 而不是白色"
    - "最下面那层" = 最外圈 (leaf/keyword 层级, 视觉上离中心最远)
    - 实现方式: ECharts sunburst 的 levels 配置按深度索引, levels[3] 对应
      keyword 层, 用 itemStyle.color 覆盖默认白/浅色
    """

    def test_sunburst_has_levels_config(self):
        """Sunburst series 必须有 levels 配置, 用于控制每层颜色。"""
        data = [{"name": "Policy", "children": [
            {"name": "Cluster A", "children": [{"name": "kw1", "value": 1}]}
        ]}]
        opt = build_sunburst(data, TCFD_THEME_CONFIG)
        assert "levels" in opt["series"][0], (
            "sunburst series must have 'levels' config to control per-depth colors"
        )

    def test_sunburst_outermost_ring_is_dark_blue(self):
        """最外圈 (keyword 层) itemStyle.color 必须是深蓝色 (hex, RGB < 50)。"""
        data = [{"name": "Policy", "children": [
            {"name": "Cluster A", "children": [{"name": "kw1", "value": 1}]}
        ]}]
        opt = build_sunburst(data, TCFD_THEME_CONFIG)
        levels = opt["series"][0]["levels"]
        # 最后一层 (keyword) 必须是深蓝色, RGB 各通道 < 80
        outermost = levels[-1]
        assert "itemStyle" in outermost, (
            f"outermost level (keyword) must have itemStyle.color, got: {outermost}"
        )
        color = outermost["itemStyle"].get("color", "")
        assert color.startswith("#") and len(color) == 7, (
            f"outermost color must be hex format like #0a1929, got: {color}"
        )
        # 验证是深色 (R, G, B 各 < 80)
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        assert max(r, g, b) < 80, (
            f"outermost color {color} not dark enough (R={r}, G={g}, B={b}); "
            "should be dark blue like #0a1929"
        )
        # 蓝色应该是主导通道 (B > R, B > G)
        assert b > r and b > g, (
            f"outermost color {color} should be blue-dominant (B > R and B > G)"
        )

    def test_sunburst_dim_level_keeps_bright_colors(self):
        """3 个 dim 层级 (Policy/Market/Technology) 必须保持各自的亮色。"""
        data = [{"name": "Policy", "children": [{"name": "A", "children": []}]}]
        opt = build_sunburst(data, TCFD_THEME_CONFIG)
        levels = opt["series"][0]["levels"]
        # dim 层 (depth=1) itemStyle.color 应该是 TCFD_THEME_CONFIG 的 3 个 dim 颜色
        dim_level = levels[1]
        assert "itemStyle" in dim_level, "dim level missing itemStyle.color"
        dim_colors = dim_level["itemStyle"]["color"]
        # dim_colors 必须是 list, 含 3 个 hex
        assert isinstance(dim_colors, list) and len(dim_colors) == 3, (
            f"dim level color must be list of 3 hex, got: {dim_colors}"
        )
        expected = [
            TCFD_THEME_CONFIG["colors"]["policy"],
            TCFD_THEME_CONFIG["colors"]["market"],
            TCFD_THEME_CONFIG["colors"]["tech"],
        ]
        for c in expected:
            assert c in dim_colors, f"missing dim color {c} in levels[1]: {dim_colors}"

    def test_sunburst_levels_count_matches_tree_depth(self):
        """levels 列表长度必须 ≥ 4 (dim + cluster + keyword + 兜底层)。

    ECharts sunburst levels 是按 depth 索引, 我们的 3-level 树
    (dim → cluster → keyword) 至少需要 4 项 (0 兜底 + 1 dim + 2 cluster + 3 keyword)。
        """
        data = [{"name": "Policy", "children": [
            {"name": "Cluster A", "children": [{"name": "kw1", "value": 1}]}
        ]}]
        opt = build_sunburst(data, TCFD_THEME_CONFIG)
        levels = opt["series"][0]["levels"]
        assert len(levels) >= 4, (
            f"sunburst must have ≥4 levels (dim/cluster/keyword + fallback), got {len(levels)}"
        )

    def test_sunburst_outermost_has_emphasis_glow(self):
        """Stage 4 emphasis 增强: 最外圈 (keyword) 悬停时发淡白光抵抗炭黑背景。

        实现: levels[-1].emphasis.itemStyle.shadowBlur + shadowColor。
        shadowColor 必须是 rgba 白光 (alpha < 0.5, 不能太刺眼)。
        """
        data = [{"name": "Policy", "children": [
            {"name": "Cluster A", "children": [{"name": "kw1", "value": 1}]}
        ]}]
        opt = build_sunburst(data, TCFD_THEME_CONFIG)
        outermost = opt["series"][0]["levels"][-1]
        assert "emphasis" in outermost, (
            f"outermost level must have emphasis config (glow on hover), got: {outermost}"
        )
        emph_style = outermost["emphasis"].get("itemStyle", {})
        assert "shadowBlur" in emph_style, (
            f"outermost emphasis.itemStyle must have shadowBlur, got: {emph_style}"
        )
        assert emph_style["shadowBlur"] > 0, (
            f"shadowBlur={emph_style['shadowBlur']} must be > 0 to create glow"
        )
        shadow_color = emph_style.get("shadowColor", "")
        # 淡白光格式: rgba(r, g, b, alpha), r=g=b=255
        assert shadow_color.startswith("rgba"), (
            f"shadowColor must be rgba format, got: {shadow_color}"
        )
        # alpha 必须 < 0.5 (不能太刺眼, 否则深蓝环变成纯白圈)
        alpha_str = shadow_color.split(",")[-1].rstrip(")").strip()
        alpha = float(alpha_str)
        assert 0 < alpha < 0.5, (
            f"shadowColor alpha={alpha} must be in (0, 0.5) for subtle glow"
        )

    def test_sunburst_cluster_level_no_fixed_color(self):
        """Stage 4 颜色继承: levels[2] (cluster) 不应写死颜色, 应依赖 per-node。

        旧实现用 #3a4554 死灰, 切断了 dim → cluster → keyword 的色彩流。
        新实现: levels[2] 留空, 由 load_sunburst_data 注入的 per-node
        itemStyle.color (父辈 dim 色 alpha=0.4) 决定。
        """
        data = [{"name": "Policy", "children": [
            {"name": "Cluster A", "children": [{"name": "kw1", "value": 1}]}
        ]}]
        opt = build_sunburst(data, TCFD_THEME_CONFIG)
        cluster_level = opt["series"][0]["levels"][2]
        # 不应该有 itemStyle.color (如果设置, 会被 ECharts 当作 fallback)
        # 但允许 itemStyle 存在 (只要不带 color 字段)
        if "itemStyle" in cluster_level:
            assert "color" not in cluster_level["itemStyle"], (
                f"cluster level (levels[2]) must NOT set itemStyle.color; "
                "color should come from per-node itemStyle injected by load_sunburst_data. "
                f"Got: {cluster_level}"
            )

    def test_sunburst_inner_radius_enlarged_for_dim_visibility(self):
        """Stage 4 round 3 调优: 最内圈 dim 层半径从 10% → 15%,
        让 Policy/Market/Technology 3 色的视觉占比更大, 不再被压成窄环显得暗淡。

        旧 radius=["10%", "85%"] (5% 宽) → 新 radius=["15%", "85%"] (10% 宽)。
        """
        data = [{"name": "Policy", "children": [
            {"name": "Cluster A", "children": [{"name": "kw1", "value": 1}]}
        ]}]
        opt = build_sunburst(data, TCFD_THEME_CONFIG)
        inner_radius = int(opt["series"][0]["radius"][0].rstrip("%"))
        assert inner_radius >= 15, (
            f"sunburst inner radius={inner_radius}% must be ≥ 15% "
            "(Stage 4 r3: enlarged from 10% to 15% for dim ring visibility)"
        )

    def test_sunburst_dim_colors_use_primed_bright_palette(self):
        """Stage 4 round 3 调亮: dim 颜色用 #79c0ff / #ffa657 / #7ee787
        (GitHub Primer accent 调色板), 比旧值 #58a6ff / #f0883e / #56d364 整体
        RGB 通道 +30~40, 暗色背景下不再显得暗淡。
        """
        data = [{"name": "Policy", "children": [
            {"name": "Cluster A", "children": [{"name": "kw1", "value": 1}]}
        ]}]
        opt = build_sunburst(data, TCFD_THEME_CONFIG)
        dim_colors = opt["series"][0]["levels"][1]["itemStyle"]["color"]
        # 必须用新的亮色调色板
        assert "#79c0ff" in dim_colors, (
            f"Policy dim color must be #79c0ff (Stage 4 r3 bright), got: {dim_colors}"
        )
        assert "#ffa657" in dim_colors, (
            f"Market dim color must be #ffa657 (Stage 4 r3 bright), got: {dim_colors}"
        )
        assert "#7ee787" in dim_colors, (
            f"Technology dim color must be #7ee787 (Stage 4 r3 bright), got: {dim_colors}"
        )
