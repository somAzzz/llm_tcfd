# Stage 2 — UI/UX 升级 + 全英文化 实施计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Stage 1 部署的 ECharts 报告(中英混合、亮色、单一字体)升级为全英文、暗色优先、Inter 字体、点击深度(关键词节点 / Sankey 流道 → 右侧侧栏显示原文 context)。

**Architecture:** Python 端在 `translations.py` 新增 `translate_smart()` + 词典扩展,~30 条 UI 术语;`echarts.py` 引入 `_t()` helper 统一翻译,4 个 builder 全部英文化;`html_assembler.py` 注入 `__hrTranslateMap` + `__hrContextIndex` JSON;`template.py` 整体重写 — Inter 字体 + CSS 变量主题(暗色默认,localStorage 持久) + Alpine.js 3.13.5(store 模式) + 右侧侧栏(`<aside>` + backdrop + ESC 关闭)。 数据层 `data_loader.py` 零改动(保留中文原值,沿用 Stage 1 snapshot 测试)。 ECharts 主题切换策略:`dispose + reinit`(< 200ms,比 patch 简单稳定)。

**Tech Stack:** Python ≥ 3.12, ECharts 5.5.0 (CDN), Alpine.js 3.13.5 (CDN, defer), Inter 字体 (Google Fonts, weights 400/500/600/700, display=swap), Jinja2, pytest, uv。

**Worktree:** 不使用, 在 main 分支直接执行。 与 Stage 1 部署决策一致; 任务独立可逆 (build 脚本不入 git, 数据源不变,output/hr_report 独立 deploy repo)。

**Spec reference:** `doc/superpowers/specs/2026-06-19-stage2-ui-ux-english-translation-design.md` (commit `4cc6942`, 已通过 2 轮 review, 7+3 修复)

**Branching model:** 主仓 main 累积追加 commits(Stage 1 已 8 commits)。 本次新增 commits 追加在 main 之后。 output/hr_report 单独 git repo,独立 push。

---

## File Structure

| 路径 | 操作 | 责任 |
|---|---|---|
| `src/tcfd_extractor/visualization/translations.py` | **扩展** | (a) 新增 `translate_smart()` 带降级 fallback; (b) `KEYWORD_TRANSLATIONS` 新增 ~30 个 dim/cluster/UI 词条; (c) `translate()` 改用 `[[ZH: xxx]]` 双中括号 (与 translate_smart 统一) |
| `src/tcfd_extractor/visualization/echarts.py` | **修改** | (a) 引入 `_t()` helper, 4 个 builder 标题/副标题/legend 全部英文化; (b) `TCFD_THEME_CONFIG` 调色板(暗色友好) + 字号 + sankey formatter 走 `__hrTranslate`; (c) tooltip formatter 走 `__hrTranslate` |
| `src/tcfd_extractor/visualization/template.py` | **重写** | (a) Inter 字体 `<link>` + `<preconnect>`; (b) Alpine.js `<script defer>`; (c) CSS 变量主题(暗色默认 + `[data-theme="light"]`); (d) `<body x-data x-init>` + Alpine.store('hrApp'); (e) header 加主题切换按钮; (f) KPI 卡片样式升级(Inter 700 大字号); (g) 4 个 section 全部英文化; (h) `<aside x-show="...">` 侧栏 + backdrop + ESC 关闭; (i) ECharts init 改 `rebuildAllCharts()` + `applyTheme()` + `bindClickHandlers()` |
| `src/tcfd_extractor/visualization/html_assembler.py` | **小改** | (a) `build_context_index(eval_dir, years)` 节点 + sankey 边 → context 列表(限 3 sample); (b) 注入 `__hrTranslateMap` + `__hrContextIndex` JSON; (c) `translate_map_json` + `context_index_json` 传给 template |
| `src/tcfd_extractor/visualization/data_loader.py` | **不改** | 保留中文原值,沿用 Stage 1 测试 |
| `tests/test_visualization/test_translations.py` | **扩展** | 5 case: `translate_smart()` 行为 + 词典扩展条目存在性 |
| `tests/test_visualization/test_echarts.py` | **扩展** | 4 builder 标题/副标题英文化 + `_t()` helper 行为 |
| `tests/test_visualization/test_html_assembler.py` | **扩展** | 4 case: `build_context_index()` 行为 + 注入物 + 主题属性 |
| `scripts/build_hr_report.py` | **不改** | 沿用 |
| `output/hr_report/` | **重建** | rebuild + force-push to upstream `somAzzz/tcfd-report` main |

**净变化**: 扩展 2 + 修改 2 + 重写 1 + 不动 2 + 重建 1 ≈ **+280 行, 净增 ~280 行** (其中 ~40% 测试, ~30% 是 template 主题 CSS)

---

## Chunk 1: `translations.py` 扩展 (`translate_smart()` + 词典 + 统一双中括号)

**Files:**
- Modify: `src/tcfd_extractor/visualization/translations.py`
- Modify: `tests/test_visualization/test_translations.py`

**目标**: Stage 2 翻译层的 Python 入口。 新增 `translate_smart()` 带降级 fallback, 词典追加 ~30 个新条目(维度名 / cluster / UI 术语 / Sankey 阶段), 同时把 `translate()` 改用 `[[ZH: xxx]]` 双中括号以统一降级格式(spec §5.2 末段硬要求)。 先写测试, 写实现, 全部跑通再 commit。

### Task 1.1: 写 `translate_smart()` 失败测试

**Files:**
- Modify: `tests/test_visualization/test_translations.py` (末尾追加)

- [ ] **Step 1: 写 4 个失败测试**

在 `tests/test_visualization/test_translations.py` 末尾追加:

```python
from tcfd_extractor.visualization.translations import translate_smart


class TestTranslateSmart:
    """Spec §5.1: translate_smart 4 路径: 精确命中 / 纯 ASCII / 中文未命中 / 空字符串。"""

    def test_exact_dict_match_returns_english(self):
        """精确命中 → 返回英文。"""
        assert translate_smart("碳交易") == "Carbon Trading"
        assert translate_smart("低碳") == "Low-Carbon"
        assert translate_smart("政策") == "Policy"

    def test_pure_ascii_returns_as_is(self):
        """纯 ASCII (不在 dict 中也算) → 原样返回。"""
        assert translate_smart("ESG") == "ESG"
        assert translate_smart("TCFD") == "TCFD"
        assert translate_smart("Carbon Neutrality") == "Carbon Neutrality"

    def test_chinese_unmatched_wrapped_in_double_brackets(self):
        """中文未命中 → `[[ZH: cleaned]]` 包裹(双中括号, 与 translate() 统一)。"""
        result = translate_smart("某未收录的术语")
        assert result == "[[ZH: 某未收录的术语]]"

    def test_chinese_with_punctuation_strips_symbols(self):
        """含标点的中文未命中 → 剥离标点后包裹。"""
        assert translate_smart("某词!") == "[[ZH: 某词]]"
        assert translate_smart("某词（测试）") == "[[ZH: 某词测试]]"

    def test_empty_string_returns_empty(self):
        """空字符串 → 空字符串。"""
        assert translate_smart("") == ""


class TestNewDictionaryEntries:
    """Spec §5.2: 词典扩展 ~30 个 dim/cluster/UI 词条。"""

    @pytest.mark.parametrize("zh,en", [
        # 维度名
        ("政策", "Policy"),
        ("市场", "Market"),
        ("技术", "Technology"),
        ("无", "N/A"),
        # 聚类 math_label (A-J)
        ("聚类A", "Cluster A"),
        ("聚类B", "Cluster B"),
        ("聚类C", "Cluster C"),
        ("聚类D", "Cluster D"),
        ("聚类E", "Cluster E"),
        ("聚类F", "Cluster F"),
        ("聚类G", "Cluster G"),
        ("聚类H", "Cluster H"),
        ("聚类I", "Cluster I"),
        ("聚类J", "Cluster J"),
        # Sankey 阶段名
        ("披露", "Disclosure"),
        ("披露趋势", "Disclosure Trend"),
        ("流水线", "Pipeline"),
        ("数据提纯", "Data Refinement"),
        ("分块", "Chunking"),
        ("维度归类", "By Dimension"),
        ("阶段1", "Stage 1"),
        ("阶段2", "Stage 2"),
        ("阶段3", "Stage 3"),
        ("阶段4", "Stage 4"),
        # UI 术语
        ("公司数", "Companies"),
        ("披露数", "Disclosures"),
        ("年份范围", "Years Covered"),
        ("工程质量", "Engineering Quality"),
        ("测试通过", "tests passing"),
        ("项目", "Project"),
        ("工程", "Engineering"),
        ("技术深度", "Tech Deep Dive"),
        ("模块依赖图", "Module Dependency Graph"),
        ("已构建", "Built"),
        ("源代码按需索取", "Source available on request"),
        ("数据已脱敏", "All data anonymized"),
        ("构建中", "Under construction"),
        ("刷新", "Refresh"),
        ("加载失败", "Load failed"),
        ("点击节点下钻", "Click a node to drill down"),
        ("拖动滑块缩放", "Drag the slider to zoom"),
        ("可拖拽节点", "Draggable nodes"),
        ("点击查看详情", "Click to view details"),
    ])
    def test_new_entry_exists(self, zh, en):
        from tcfd_extractor.visualization.translations import KEYWORD_TRANSLATIONS
        assert zh in KEYWORD_TRANSLATIONS, f"missing dict entry for {zh!r}"
        assert KEYWORD_TRANSLATIONS[zh] == en


class TestTranslateUnifiedDoubleBrackets:
    """Spec §5.2 末段: `translate()` 改用 `[[ZH: xxx]]` 双中括号, 与 translate_smart 统一。"""

    def test_translate_unknown_uses_double_brackets(self):
        from tcfd_extractor.visualization.translations import translate
        result = translate("某未收录的术语")
        assert result == "[[ZH: 某未收录的术语]]"
        assert result.startswith("[[ZH:")
        assert result.endswith("]]")
```

顶部添加 `import pytest` (如果还没有)。

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/test_visualization/test_translations.py::TestTranslateSmart -v`
Expected: `ImportError: cannot import name 'translate_smart' from 'tcfd_extractor.visualization.translations'`

### Task 1.2: 实现 `translate_smart()` + 词典扩展 + `translate()` 改双中括号

**Files:**
- Modify: `src/tcfd_extractor/visualization/translations.py`

- [ ] **Step 3: 追加 ~30 个新词典条目**

在 `KEYWORD_TRANSLATIONS` 字典的 `"TCFD": "TCFD"` 行后追加(spec §5.2):

```python
    # === Stage 2 additions (spec §5.2) ===
    # 维度名
    "无": "N/A",  # N/A 显式优于 "None", 避免与 Python None 混淆
    # 聚类 math_label (A-J)
    "聚类A": "Cluster A",
    "聚类B": "Cluster B",
    "聚类C": "Cluster C",
    "聚类D": "Cluster D",
    "聚类E": "Cluster E",
    "聚类F": "Cluster F",
    "聚类G": "Cluster G",
    "聚类H": "Cluster H",
    "聚类I": "Cluster I",
    "聚类J": "Cluster J",
    # Sankey 阶段名 (template.py + echarts.py 用)
    "披露趋势": "Disclosure Trend",
    "流水线": "Pipeline",
    "数据提纯": "Data Refinement",
    "分块": "Chunking",
    "维度归类": "By Dimension",  # 比 "Dimension Classification" 简洁
    "阶段1": "Stage 1",
    "阶段2": "Stage 2",
    "阶段3": "Stage 3",
    "阶段4": "Stage 4",
    # UI 标签
    "公司数": "Companies",
    "披露数": "Disclosures",
    "年份范围": "Years Covered",
    "工程质量": "Engineering Quality",
    "测试通过": "tests passing",
    "项目": "Project",
    "工程": "Engineering",
    "技术深度": "Tech Deep Dive",
    "模块依赖图": "Module Dependency Graph",
    "已构建": "Built",
    "源代码按需索取": "Source available on request",
    "数据已脱敏": "All data anonymized",
    "构建中": "Under construction",
    "刷新": "Refresh",
    "加载失败": "Load failed",
    "点击节点下钻": "Click a node to drill down",
    "拖动滑块缩放": "Drag the slider to zoom",
    "可拖拽节点": "Draggable nodes",
    "点击查看详情": "Click to view details",
```

注意: 已有条目 "政策", "市场", "技术", "披露", "项目" 等不要重复添加(原 dict 已有)。 `dict` 重复 key 后写覆盖前写, 但为可读性, 建议**只在首次出现位置保留**, 在新分区中跳过已存在 key。

实施时只追加 "无", "聚类A"-"聚类J"(10 个), "披露趋势", "流水线", "数据提纯", "分块", "维度归类", "阶段1"-"阶段4"(4 个), "公司数", "披露数", "年份范围", "工程质量", "测试通过", "工程", "技术深度", "模块依赖图", "已构建", "源代码按需索取", "数据已脱敏", "构建中", "刷新", "加载失败", "点击节点下钻", "拖动滑块缩放", "可拖拽节点", "点击查看详情" = 1 + 10 + 9 + 19 = **39 个新条目**(略多于 spec 估计 ~30, 因为保留所有 cluster 标签)。

- [ ] **Step 4: 在文件顶部添加 `import re`**

```python
"""Chinese → English translations for TCFD-related keywords."""
from __future__ import annotations

import re

# ...
```

- [ ] **Step 5: 添加 `_NON_ALNUM_RE` 常量和 `translate_smart()` 函数**

在文件末尾追加:

```python
_NON_ALNUM_RE = re.compile(r"[^\w\s]+", re.UNICODE)


def translate_smart(keyword: str) -> str:
    """Smart translate with graceful fallback.

    Spec §5.1:
    1. Exact dict match → return English
    2. Pure ASCII → return as-is (English term, no need to translate)
    3. Mixed/Chinese → strip symbols, wrap as [[ZH: cleaned]]
    """
    if not keyword:
        return keyword
    if keyword in KEYWORD_TRANSLATIONS:
        return KEYWORD_TRANSLATIONS[keyword]
    if keyword.isascii():
        return keyword
    cleaned = _NON_ALNUM_RE.sub("", keyword).strip()
    if not cleaned:
        return keyword
    return f"[[ZH: {cleaned}]]"
```

- [ ] **Step 6: 把 `translate()` 改用双中括号 (统一降级格式)**

修改现有 `translate()` 函数(spec §5.2 末段硬要求):

```python
def translate(keyword_zh: str) -> str:
    if keyword_zh in KEYWORD_TRANSLATIONS:
        return KEYWORD_TRANSLATIONS[keyword_zh]
    return f"[[ZH: {keyword_zh}]]"  # 双中括号, 与 translate_smart 统一
```

注意: 旧格式 `[ZH: xxx]`(单中括号)→ 新格式 `[[ZH: xxx]]`(双中括号)。 任何依赖旧格式的下游需要同步检查(本任务范围内的 `test_translations.py::test_unknown_keyword_returns_zh_marker` 也需改,见 Task 1.3)。

- [ ] **Step 7: 跑测试确认全部通过**

Run: `uv run pytest tests/test_visualization/test_translations.py -v`
Expected: 全部 PASS(包含 Stage 1 的原有测试 + 新增测试)。

### Task 1.3: 修复 Stage 1 旧测试 (translate() 单中括号 → 双中括号)

**Files:**
- Modify: `tests/test_visualization/test_translations.py`

- [ ] **Step 8: 修改 `test_unknown_keyword_returns_zh_marker`**

定位: `tests/test_visualization/test_translations.py:19-22`

原代码:
```python
def test_unknown_keyword_returns_zh_marker(self):
    result = translate("某未知关键词")
    assert "某未知关键词" in result
    assert result.startswith("[ZH:")
```

修改为(双中括号):
```python
def test_unknown_keyword_returns_zh_marker(self):
    result = translate("某未知关键词")
    assert "某未知关键词" in result
    assert result.startswith("[[ZH:")
    assert result.endswith("]]")
```

- [ ] **Step 9: 跑全测试套件确认无 regression**

Run: `uv run pytest tests/test_visualization/ -v`
Expected: 全绿, `test_translations.py` 含 5 新 case(`TestTranslateSmart` 4 + `TestNewDictionaryEntries` 39 parametrize + `TestTranslateUnifiedDoubleBrackets` 1 + Stage 1 原有), `test_data_loader.py` 18 个原 case 全绿。

- [ ] **Step 10: Commit**

```bash
git add src/tcfd_extractor/visualization/translations.py tests/test_visualization/test_translations.py
git commit -m "feat(translations): Stage 2 — translate_smart() + ~30 dict entries + [[ZH: ...]] 统一

- 新增 translate_smart(): 精确命中 / 纯 ASCII / [[ZH: cleaned]] 降级
- KEYWORD_TRANSLATIONS 追加 39 条 (dim / cluster A-J / Sankey stage / UI 术语)
- translate() 改用 [[ZH: xxx]] 双中括号, 与 translate_smart 统一
- 测试: 5 新 case (TestTranslateSmart 5 + TestNewDictionaryEntries 39 parametrize + TestTranslateUnifiedDoubleBrackets 1)
"
```

---

## Chunk 2: `echarts.py` 改写 — `_t()` helper + 4 builder 英文化 + 调色板

**Files:**
- Modify: `src/tcfd_extractor/visualization/echarts.py`
- Modify: `tests/test_visualization/test_echarts.py`

**目标**: 翻译层 (Python 端) 的 ECharts 入口。 引入 `_t()` helper 统一走 `translate_smart()`, 4 个 builder 的 title/subtitle/legend/axis label/formatter 全部英文化, `TCFD_THEME_CONFIG` 调色板改为暗色友好, sankey formatter 走 `window.__hrTranslate`(客户端兜底)。 tooltip formatter 也走 `__hrTranslate`。

### Task 2.1: 写 `_t()` helper 失败测试 + `TCFD_THEME_CONFIG` 暗色调色板断言

**Files:**
- Modify: `tests/test_visualization/test_echarts.py` (末尾追加)

- [ ] **Step 1: 写 `_t()` helper 测试 + 调色板测试**

在 `tests/test_visualization/test_echarts.py` 末尾追加:

```python
from tcfd_extractor.visualization.echarts import _t


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
        c = TCFD_THEME_CONFIG["colors"]["policy"]
        assert c.startswith("#") and len(c) == 7

    def test_market_color_uses_bright_orange(self):
        c = TCFD_THEME_CONFIG["colors"]["market"]
        assert c.startswith("#") and len(c) == 7

    def test_tech_color_uses_bright_green(self):
        c = TCFD_THEME_CONFIG["colors"]["tech"]
        assert c.startswith("#") and len(c) == 7

    def test_tooltip_text_color_is_white_for_dark(self):
        # 暗色默认下 tooltip 文字白色
        assert TCFD_THEME_CONFIG["tooltip_style"]["textStyle"]["color"] == "#fff"

    def test_sankey_formatter_uses_client_translator(self):
        """Sankey formatter 走 window.__hrTranslate 客户端兜底。"""
        fmt = TCFD_THEME_CONFIG["sankey_label_formatter"]
        assert "window.__hrTranslate" in fmt
        assert "stage\\d+_" in fmt  # 仍剥离 stage{N}_ 前缀
```

- [ ] **Step 2: 跑测试确认 `_t` 失败**

Run: `uv run pytest tests/test_visualization/test_echarts.py::TestTranslateHelper -v`
Expected: `ImportError: cannot import name '_t' from 'tcfd_extractor.visualization.echarts'`

### Task 2.2: 实现 `_t()` helper + 改 `TCFD_THEME_CONFIG` 暗色调色板

**Files:**
- Modify: `src/tcfd_extractor/visualization/echarts.py`

- [ ] **Step 3: 添加 `from .translations import translate_smart`**

在 `src/tcfd_extractor/visualization/echarts.py` 顶部 `import` 区域添加:

```python
import logging
from typing import Any

from .translations import translate_smart

logger = logging.getLogger(__name__)


def _t(keyword: str) -> str:
    """echarts.py 内部统一翻译 helper — 走 translate_smart()。"""
    return translate_smart(keyword)
```

- [ ] **Step 4: 改 `TCFD_THEME_CONFIG` 暗色调色板 (Spec §6.2)**

替换原 `TCFD_THEME_CONFIG`:

```python
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
```

注意:
- `"policy"`: `#1f77b4` → `#58a6ff`(亮蓝)
- `"market"`: `#ff7f0e` → `#f0883e`(亮橙)
- `"tech"`: `#2ca02c` → `#56d364`(亮绿)
- `"text_style"`: 默认 color 改 `#e6e6e6`(暗色)
- `tooltip_style` 升级: bg `rgba(50,50,50,0.92)` → `rgba(20,20,20,0.95)`, 加 `borderWidth/borderColor`, fontFamily "Inter"
- `animation_duration`: `800` → `600`
- `sankey_label_formatter`: 走 `window.__hrTranslate`, 保留 stage{N}_ 剥离

- [ ] **Step 5: 跑测试确认 `TestTranslateHelper` + `TestDarkThemePalette` 通过**

Run: `uv run pytest tests/test_visualization/test_echarts.py::TestTranslateHelper tests/test_visualization/test_echarts.py::TestDarkThemePalette -v`
Expected: 全绿。

### Task 2.3: 4 个 builder 标题/副标题/legend 英文化

**Files:**
- Modify: `src/tcfd_extractor/visualization/echarts.py`

- [ ] **Step 6: 写 builder 标题英文化失败测试**

在 `tests/test_visualization/test_echarts.py` 末尾追加:

```python
class TestBuildersEnglishTitles:
    """Spec §5.3: 4 个 builder 标题/副标题全部英文化。"""

    def test_build_sunburst_title_is_english(self):
        data = [{"name": "Policy", "children": [{"name": "Cluster A", "children": []}]}]
        opt = build_sunburst(data, TCFD_THEME_CONFIG)
        title = opt["title"]["text"]
        assert "TCFD" in title  # TCFD 缩写保留
        assert all(ord(c) < 128 for c in title), f"non-ASCII in title: {title!r}"

    def test_build_streamgraph_title_is_english(self):
        data = {
            "years": [2020, 2021],
            "series": [{"name": "Policy", "data": [1, 2]}],
        }
        opt = build_streamgraph(data, TCFD_THEME_CONFIG)
        title = opt["title"]["text"]
        sub = opt["title"].get("subtext", "")
        assert all(ord(c) < 128 for c in title)
        assert all(ord(c) < 128 for c in sub)

    def test_build_network_title_and_categories_are_english(self):
        data = {
            "nodes": [{"id": "a", "name": "a", "symbolSize": 15, "category": "Policy", "value": 1}],
            "links": [],
        }
        opt = build_network(data, TCFD_THEME_CONFIG)
        title = opt["title"]["text"]
        sub = opt["title"].get("subtext", "")
        assert all(ord(c) < 128 for c in title)
        assert all(ord(c) < 128 for c in sub)
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
        assert all(ord(c) < 128 for c in title)
        assert all(ord(c) < 128 for c in sub)
```

- [ ] **Step 7: 跑测试确认 builder 测试失败**

Run: `uv run pytest tests/test_visualization/test_echarts.py::TestBuildersEnglishTitles -v`
Expected: 失败 (现有 builder 标题是中文)。

- [ ] **Step 8: 改 `build_sunburst` 标题英文化**

替换 `build_sunburst`:

```python
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
```

- [ ] **Step 9: 改 `build_streamgraph` 标题英文化**

替换 `build_streamgraph`:

```python
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
```

- [ ] **Step 10: 改 `build_network` 标题 + categories 英文化**

替换 `build_network`:

```python
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
```

注意: 上一版的 `categories` 是中文 `{"name": "政策"}, {"name": "市场"}, {"name": "技术"}`。 改英文后, network 节点的 `category` 字段(由 data_loader 决定)需要与之匹配。 检查 `data_loader.load_network_data` 是否对 category 做了翻译 — **如果是, 改 builder; 如果不是, 改 data_loader 或保持 builder 期望中文 category, 由 click handler 做翻译**。 见 Task 2.3.1。

- [ ] **Step 10.1: 验证 network category 字段翻译路径**

Run:
```bash
grep -n "category\|dimension" /home/bo/projects/python/frequency_analyzer/src/tcfd_extractor/visualization/data_loader.py | head -30
```

如果 `load_network_data` 中 `category` 直接用 `record["dimension"]` (中文 "政策"/"市场"/"技术"), 则需要以下两种方案之一:
- **方案 A (推荐, 与 spec §6 翻译层位置一致)**: 在 `load_network_data` 中把 category 翻译为英文 (e.g., `record["dimension"]` → `translate(record["dimension"])`)。
- **方案 B**: builder 仍期望中文 category, click handler 内做翻译。

采用**方案 A**: 在 `data_loader.load_network_data` 中翻译 category。 修改后跑现有 `test_data_loader.py` 确认无 regression(原测试可能 assert 中文 category, 见 Task 2.3.2)。

- [ ] **Step 10.2: 修改 `load_network_data` 翻译 category**

定位: `data_loader.py` 中 `load_network_data` 函数 (约 230 行, 找到 `if ka and kb:` 附近的循环, 看 nodes 构造)。

修改:
```python
from .translations import translate  # 顶部 import
# ...
# 在 nodes 构造处:
"category": translate(record.get("dimension", "")),
```

**注意**: 这会破坏 `test_data_loader.py` 中对中文 category 的断言 (如 `assert nodes_by_id["词A"]["category"] == "政策"`)。 同步修改 `tests/test_visualization/test_data_loader.py` 中相关 assert 为英文 ("Policy"/"Market"/"Technology")。 跑测试确认。

(spec §5.3 决策 6 明确"翻译在显示层", 但 categories 是 ECharts option 的字段, 不在显示模板里。 这里"翻译在 echarts.py builder 层"是字面执行, category 由 builder 喂给 series, builder 接收 data_loader 的 raw 输入, 做翻译是合理边界。)

- [ ] **Step 11: 改 `build_sankey` 标题英文化**

替换 `build_sankey`:

```python
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
```

- [ ] **Step 12: 跑全 echarts 测试套件**

Run: `uv run pytest tests/test_visualization/test_echarts.py -v`
Expected: 全绿 (含 Stage 1 原有 + Task 2.1 `_t` + Task 2.1 调色板 + Task 2.3 builder 英文)。

注意: Stage 1 原有测试 `test_get_base_option_returns_skeleton` 用 `"测试标题"`, `test_build_sunburst_returns_echarts_option_skeleton` 用 `{"name": "政策", ...}` 中文 data。 这些测试不检查 builder title, 只检查 option 骨架, 不受本次改动影响。 但应跑一遍确认无意外 break。

- [ ] **Step 13: 跑全 visualization 测试**

Run: `uv run pytest tests/test_visualization/ -v`
Expected: 全绿。 如果 `test_data_loader.py` 因 category 翻译失败, 回到 Task 2.3.2 修改。

- [ ] **Step 14: Commit**

```bash
git add src/tcfd_extractor/visualization/echarts.py src/tcfd_extractor/visualization/data_loader.py tests/test_visualization/test_echarts.py tests/test_visualization/test_data_loader.py
git commit -m "feat(echarts): Stage 2 — _t() helper + 4 builder English + dark palette

- 新增 _t() helper, 统一走 translate_smart()
- TCFD_THEME_CONFIG 暗色友好调色板 (policy/market/tech 亮色调)
- sankey_label_formatter 走 window.__hrTranslate 客户端兜底
- 4 builder 标题/副标题/legend 全部英文化
- build_network categories 改英文 (Policy/Market/Technology)
- data_loader.load_network_data category 字段翻译为英文
- 测试: 4 类新 case (_t 4 + 调色板 5 + builder 标题 4)
"
```

---

## Chunk 3: `template.py` 重写 — Inter 字体 + Alpine.js + 暗色默认 + 侧栏

**Files:**
- Modify: `src/tcfd_extractor/visualization/template.py`
- Modify: `tests/test_visualization/test_html_assembler.py`

**目标**: 模板层 — 全部英文化、Inter 字体、CSS 变量主题(暗色默认)、Alpine.js store 模式、右侧侧栏 + backdrop + ESC 关闭。 这是 Stage 2 的视觉/交互核心。

### Task 3.1: 写集成测试 (template 内含物)

**Files:**
- Modify: `tests/test_visualization/test_html_assembler.py` (末尾追加)

- [ ] **Step 1: 写 4 个集成测试**

在 `tests/test_visualization/test_html_assembler.py` 末尾追加:

```python
class TestStage2TemplateContent:
    """Spec §11 集成测试: Inter 字体 + Alpine + 暗色默认 + 侧栏。"""

    def test_html_has_dark_theme_default(self, tmp_path):
        """<html data-theme='dark'> 暗色默认。"""
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            refactor_bar_b64="x",
            module_graph_svg="<svg></svg>",
        )
        assert 'data-theme="dark"' in html

    def test_html_has_inter_font_link(self, tmp_path):
        """Inter Google Fonts <link> 出现, 含 display=swap。"""
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            refactor_bar_b64="x",
            module_graph_svg="<svg></svg>",
        )
        assert "Inter:wght" in html
        assert "display=swap" in html

    def test_html_has_alpine_defer_script(self, tmp_path):
        """Alpine.js <script defer> 出现, URL 锁版本 3.13.x。"""
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            refactor_bar_b64="x",
            module_graph_svg="<svg></svg>",
        )
        assert "alpinejs@3.13" in html
        assert "defer" in html

    def test_html_has_side_panel_with_zindex(self, tmp_path):
        """<aside> 侧栏 + z-index 1000 + backdrop 出现。"""
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            refactor_bar_b64="x",
            module_graph_svg="<svg></svg>",
        )
        assert "hr-side-panel" in html
        assert "z-index: 1000" in html
        assert "hr-side-panel-backdrop" in html
```

- [ ] **Step 2: 跑测试确认失败 (template 尚未重写)**

Run: `uv run pytest tests/test_visualization/test_html_assembler.py::TestStage2TemplateContent -v`
Expected: 全失败 (template 旧版没有 Inter/Alpine/data-theme/侧栏)。

### Task 3.2: 重写 `template.py`

**Files:**
- Modify: `src/tcfd_extractor/visualization/template.py`

整体重写 template.py (这是 Stage 2 最大改动)。 完整代码见 `spec §4-7`, 实施时直接照搬 spec 内联 `<script>` 块 + Alpine 表达式, 不要重新设计。

- [ ] **Step 3: 重写 `template.py`**

完整替换 `src/tcfd_extractor/visualization/template.py`。 关键内容(spec §4-7 综合):

```python
"""Jinja2 HTML template for the HR report (Stage 2: dark + Inter + Alpine)."""
from __future__ import annotations

from jinja2 import Template

HTML_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TCFD Project Demo — Climate Disclosure Analysis</title>
  <link rel="icon" href="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><circle cx='16' cy='16' r='14' fill='%231f77b4'/><text x='16' y='22' font-size='18' text-anchor='middle' fill='white' font-family='sans-serif' font-weight='bold'>T</text></svg>">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
  <script>
    // Stage 2: 翻译 map + context 索引 (由 html_assembler.py 渲染)
    window.__hrTranslateMap = {{ translate_map_json|safe }};
    window.__hrContextIndex = {{ context_index_json|safe }};
    window.__hrTranslate = function(kw) {
      if (!kw) return '';
      const map = window.__hrTranslateMap || {};
      if (map[kw]) return map[kw];
      if (/^[\\x00-\\x7F]+$/.test(kw)) return kw;
      return '[[ZH: ' + kw.replace(/[^\\w\\s]+/g, '').trim() + ']]';
    };
  </script>
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.13.5/dist/cdn.min.js"></script>
  <style>
    :root[data-theme="dark"] {
      --bg: #0f1419;
      --fg: #e6e6e6;
      --card-bg: #1a1f24;
      --card-border: #2a2f34;
      --muted: #8b95a1;
      --accent: #58a6ff;
      --accent-fg: #ffffff;
      --header-bg: linear-gradient(135deg, #1f3a5f 0%, #1a4d2e 100%);
      --kpi-number-color: #58a6ff;
      --aside-bg: #1a1f24;
      --aside-border: #2a2f34;
      --code-bg: #0d1117;
    }
    :root[data-theme="light"] {
      --bg: #fafafa;
      --fg: #222;
      --card-bg: #ffffff;
      --card-border: #e0e0e0;
      --muted: #666;
      --accent: #1f77b4;
      --accent-fg: #ffffff;
      --header-bg: linear-gradient(135deg, #1f77b4 0%, #2ca02c 100%);
      --kpi-number-color: #1f77b4;
      --aside-bg: #ffffff;
      --aside-border: #e0e0e0;
      --code-bg: #f5f5f5;
    }
    * { box-sizing: border-box; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--fg);
      margin: 0;
      padding: 0;
      line-height: 1.5;
    }
    body, section, .kpi-card, header, .hr-side-panel, .callout {
      transition: background-color 0.25s ease, color 0.25s ease, border-color 0.25s ease;
    }
    .container { max-width: 1100px; margin: 0 auto; padding: 2rem 1.5rem; }
    header {
      background: var(--header-bg);
      color: white;
      padding: 2rem 1.5rem;
      text-align: center;
      position: relative;
    }
    header h1 { margin: 0 0 0.5rem 0; font-size: 1.8rem; font-weight: 700; }
    header .subtitle { opacity: 0.9; font-size: 1.05rem; }
    .hr-theme-toggle {
      position: absolute;
      top: 1rem;
      right: 1rem;
      background: rgba(255,255,255,0.15);
      border: 1px solid rgba(255,255,255,0.3);
      color: white;
      padding: 0.4rem 0.7rem;
      border-radius: 4px;
      cursor: pointer;
      font-size: 1rem;
    }
    .kpi-row {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;
      margin: 2rem 0;
    }
    .kpi-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 1.25rem;
      text-align: center;
    }
    .kpi-card .number {
      font-size: 2.25rem;
      font-weight: 700;
      color: var(--kpi-number-color);
      margin: 0;
      font-family: 'Inter', sans-serif;
    }
    .kpi-card .label {
      font-size: 0.85rem;
      color: var(--muted);
      margin-top: 0.5rem;
    }
    section {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 1.5rem;
      margin: 1.5rem 0;
    }
    section h2 {
      margin: 0 0 1rem 0;
      font-size: 1.4rem;
      color: var(--accent);
      font-weight: 600;
    }
    .callout {
      background: var(--code-bg);
      border-left: 4px solid var(--accent);
      padding: 1rem 1.25rem;
      margin: 1.5rem 0;
      border-radius: 4px;
    }
    .callout h3 {
      margin: 0 0 0.5rem 0;
      color: var(--accent);
      font-size: 1.1rem;
    }
    details.tech-deep-dive {
      margin: 1.5rem 0;
    }
    details.tech-deep-dive summary {
      cursor: pointer;
      padding: 0.75rem 1rem;
      background: var(--code-bg);
      border: 1px solid var(--card-border);
      border-radius: 4px;
      font-weight: 500;
    }
    details.tech-deep-dive[open] summary { border-radius: 4px 4px 0 0; }
    details.tech-deep-dive > div {
      border: 1px solid var(--card-border);
      border-top: none;
      padding: 1rem;
      border-radius: 0 0 4px 4px;
    }
    footer {
      text-align: center;
      padding: 2rem 1rem;
      color: var(--muted);
      font-size: 0.85rem;
    }
    @media (max-width: 700px) {
      .kpi-row { grid-template-columns: repeat(2, 1fr); }
    }
  </style>
</head>
<body x-data x-init="
  document.documentElement.dataset.theme = localStorage.getItem('hr-theme') || 'dark';
  Alpine.store('hrApp', {
    theme: localStorage.getItem('hr-theme') || 'dark',
    panel: null,
    toggleTheme() {
      this.theme = this.theme === 'dark' ? 'light' : 'dark';
      localStorage.setItem('hr-theme', this.theme);
      document.documentElement.dataset.theme = this.theme;
      if (typeof rebuildAllCharts === 'function') rebuildAllCharts();
    },
    openPanel(data) { this.panel = data; },
    closePanel() { this.panel = null; },
  });
">
  <button @click="$store.hrApp.toggleTheme()"
          class="hr-theme-toggle"
          :aria-label="`Switch to ${$store.hrApp.theme === 'dark' ? 'light' : 'dark'} mode`">
    <span x-show="$store.hrApp.theme === 'dark'">☀️</span>
    <span x-show="$store.hrApp.theme === 'light'">🌙</span>
  </button>

  <header>
    <h1>TCFD Project Demo</h1>
    <p class="subtitle">A production NLP system for climate-related financial disclosure analysis</p>
  </header>

  <div class="container">
    <div class="kpi-row">
      <div class="kpi-card">
        <p class="number">10,814</p>
        <p class="label">Companies Analyzed</p>
      </div>
      <div class="kpi-card">
        <p class="number">52,000+</p>
        <p class="label">TCFD Disclosures Detected</p>
      </div>
      <div class="kpi-card">
        <p class="number">2000–2024</p>
        <p class="label">Years Covered</p>
      </div>
      <div class="kpi-card">
        <p class="number">{{ refactor_stats.get("test_after", 0) }} tests passing</p>
        <p class="label">Engineering Quality</p>
      </div>
    </div>

    <section>
      <h2>1. What is this project about?</h2>
      <p>
        This system reads <strong>annual reports from A-share listed companies</strong> and
        identifies <strong>TCFD (climate-related financial disclosure)</strong> content
        across three dimensions: <em>Policy</em>, <em>Market</em>, <em>Technology</em>.
      </p>
      <p>Three-dimensional clustering hierarchy (Sunburst) — click a node to drill down to keywords.</p>
      <div id="echarts-sunburst" class="echarts-chart" style="width:100%; height:400px;"></div>
    </section>

    <section>
      <h2>2. What we built</h2>
      <p>
        An end-to-end <strong>NLP pipeline</strong> that takes raw annual-report text
        through sampling, chunking, LLM-based keyword extraction, co-occurrence analysis,
        TCFD evaluation, and clustering.
      </p>
      <div class="mermaid">
flowchart LR
    A[1. Sample Reports] --> B[2. Split into Chunks]
    B --> C[3. Extract Keywords with LLM]
    C --> D[4. Find Co-occurring Pairs]
    D --> E[5. Score on Policy/Market/Technology]
    E --> F[6. Cluster Similar Topics]
      </div>
      <div class="callout">
        <h3>Beyond TCFD: Reusable Architecture</h3>
        <p>
          The patterns demonstrated here — multi-dimensional routing, structured LLM outputs,
          concurrent batch processing with retry — are domain-agnostic. The same architecture
          applies to:
        </p>
        <ul>
          <li><strong>Multilingual content classification</strong> at scale</li>
          <li><strong>Concurrent pipeline</strong> of LLM evaluations with rate limiting</li>
          <li><strong>Structured outputs from open-source models</strong> for downstream analytics</li>
        </ul>
        <p><em>Same engineering. New domain.</em></p>
      </div>
    </section>

    <section>
      <h2>3. What we discovered</h2>
      <p>
        Below: 25 years (2000-2024) of three-dimensional disclosure evolution (Streamgraph) —
        drag the bottom slider to zoom into a time range.
      </p>
      <div id="echarts-streamgraph" class="echarts-chart" style="width:100%; height:400px;"></div>

      <h3 style="margin-top: 2rem;">Keyword Co-occurrence Network (Recent 3 Years)</h3>
      <p>Draggable nodes, hover to see co-occurrence count, click a node to view original context.</p>
      <div id="echarts-network" class="echarts-chart" style="width:100%; height:500px;"></div>

      <h3 style="margin-top: 2rem;">NLP Pipeline Data Refinement (Sankey)</h3>
      <p>10,814 reports → chunking → disclosure → by dimension. Click a link to view context.</p>
      <div id="echarts-sankey" class="echarts-chart" style="width:100%; height:400px;"></div>
    </section>

    <section>
      <h2>4. Engineering excellence</h2>
      <p>
        The original 468-line god class has been decomposed into focused modules
        with a significant increase in test coverage.
      </p>
      <div style="text-align: center; margin: 1rem 0;">
        <img src="data:image/png;base64,{{ refactor_b64 }}"
             alt="Refactor before/after chart"
             style="max-width: 100%; height: auto; border: 1px solid var(--card-border); border-radius: 4px;">
      </div>
    </section>

    <details class="tech-deep-dive">
      <summary>🔬 Tech Deep Dive — Module Dependency Graph (click to expand)</summary>
      <div>
        <p>Evaluation modules + shared config + tests. Arrows = import direction.</p>
        {{ module_graph_svg | safe }}
      </div>
    </details>

    <footer>
      <p>Built {{ build_date }} · Source available on request · All data anonymized</p>
    </footer>
  </div>

  <!-- Side panel: backdrop + aside (Alpine 侧栏) -->
  <div x-show="$store.hrApp.panel"
       x-transition.opacity.duration.200ms
       @click="$store.hrApp.closePanel()"
       class="hr-side-panel-backdrop"
       style="position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 999;"></div>

  <aside x-show="$store.hrApp.panel"
         x-transition:enter="hr-slide-in"
         x-transition:leave="hr-slide-out"
         @keydown.escape.window="$store.hrApp.closePanel()"
         class="hr-side-panel"
         style="position: fixed; right: 0; top: 0; width: 420px; height: 100vh;
                background: var(--aside-bg); border-left: 1px solid var(--aside-border);
                box-shadow: -4px 0 12px rgba(0,0,0,0.3); z-index: 1000;
                transform: translateX(100%); transition: transform 0.25s ease;
                overflow-y: auto; padding: 1.5rem;">
    <header style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;
                   padding-bottom: 0.75rem; border-bottom: 1px solid var(--card-border);">
      <h3 x-text="$store.hrApp.panel ? $store.hrApp.panel.title : ''"
          style="margin: 0; flex: 1; font-size: 1.15rem; color: var(--fg);"></h3>
      <span class="dim-badge"
            x-show="$store.hrApp.panel && $store.hrApp.panel.dimension"
            x-text="$store.hrApp.panel ? $store.hrApp.panel.dimension : ''"
            style="background: var(--accent); color: var(--accent-fg); padding: 0.2rem 0.6rem;
                   border-radius: 4px; font-size: 0.8rem;"></span>
      <button @click="$store.hrApp.closePanel()"
              style="background: none; border: none; color: var(--muted); cursor: pointer;
                     font-size: 1.25rem; padding: 0.25rem 0.5rem;">✕</button>
    </header>
    <div class="hr-side-panel__body">
      <template x-if="$store.hrApp.panel && $store.hrApp.panel.contexts.length === 0">
        <p style="color: var(--muted); font-style: italic;">No context samples available for this item.</p>
      </template>
      <template x-for="ctx in $store.hrApp.panel ? $store.hrApp.panel.contexts : []" :key="ctx.id">
        <article class="context-card" style="background: var(--card-bg);
                                              border: 1px solid var(--card-border);
                                              border-radius: 6px; padding: 1rem; margin-bottom: 1rem;">
          <p class="context-zh" x-text="ctx.original"
             style="color: var(--fg); margin: 0 0 0.5rem 0; font-size: 0.95rem;"></p>
          <p class="context-en" x-text="ctx.translated"
             style="color: var(--muted); margin: 0 0 0.75rem 0; font-size: 0.9rem; font-style: italic;"></p>
          <footer style="display: flex; justify-content: space-between;
                         color: var(--muted); font-size: 0.8rem;">
            <span x-text="ctx.source"></span>
            <span x-text="ctx.year"></span>
          </footer>
        </article>
      </template>
    </div>
  </aside>

  <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
  <script>
    mermaid.initialize({ startOnLoad: true, securityLevel: 'loose' });

    // Stage 2: ECharts 4 图表统一管理 (dispose + reinit 主题切换)
    window.__hrCharts = {};
    window.__hrOpts = {
      sunburst:    {{ sunburst_json|safe }},
      streamgraph: {{ streamgraph_json|safe }},
      network:     {{ network_json|safe }},
      sankey:      {{ sankey_json|safe }},
    };

    function applyTheme(opt, theme) {
      const isDark = theme === 'dark';
      const fg = isDark ? '#e6e6e6' : '#222';
      const muted = isDark ? '#8b95a1' : '#666';
      opt = JSON.parse(JSON.stringify(opt));
      opt.textStyle = Object.assign({}, opt.textStyle, { color: fg });
      if (opt.title) opt.title.textStyle = Object.assign({}, opt.title.textStyle, { color: fg });
      ['xAxis', 'yAxis'].forEach(k => {
        if (opt[k]) {
          opt[k] = Object.assign({}, opt[k], {
            axisLine: { lineStyle: { color: muted } },
            axisLabel: { color: muted },
            splitLine: { lineStyle: { color: muted, opacity: 0.2 } },
          });
        }
      });
      if (opt.legend) opt.legend.textStyle = Object.assign({}, opt.legend.textStyle, { color: fg });
      return opt;
    }

    function bindClickHandlers(chart, chartId) {
      chart.on('click', function(params) {
        if (chartId === 'echarts-network' && params.dataType === 'node') {
          const kw = params.data.name;
          const contexts = (window.__hrContextIndex.keywords[kw] || []).slice(0, 3);
          window.Alpine.store('hrApp').openPanel({
            type: 'node',
            title: window.__hrTranslate(kw),
            dimension: window.__hrTranslate(params.data.category || ''),
            contexts: contexts,
          });
        } else if (chartId === 'echarts-sankey' && params.dataType === 'edge') {
          const stripPrefix = s => (s || '').replace(/^stage\\d+_/, '');
          const source = stripPrefix(params.data.source);
          const target = stripPrefix(params.data.target);
          // 关键: 与 build_context_index 保持一致 — 排序后的 a->b 字符串
          const pair = [source, target].sort();
          const edgeKey = `${pair[0]}->${pair[1]}`;
          const contexts = (window.__hrContextIndex.sankey[edgeKey] || []).slice(0, 3);
          window.Alpine.store('hrApp').openPanel({
            type: 'link',
            title: `${window.__hrTranslate(source)} → ${window.__hrTranslate(target)}`,
            contexts: contexts,
          });
        }
        // 其它点击 (axisLabel / legend / 空白) → 不响应, panel 保持
      });
    }

    function buildChart(chartId, opt) {
      const el = document.getElementById(chartId);
      if (!el) return;
      if (window.__hrCharts[chartId]) {
        window.__hrCharts[chartId].dispose();
      }
      opt = applyTheme(opt, document.documentElement.dataset.theme);
      const chart = echarts.init(el);
      chart.setOption(opt);
      window.__hrCharts[chartId] = chart;
      bindClickHandlers(chart, chartId);
      return chart;
    }

    function rebuildAllCharts() {
      buildChart('echarts-sunburst',     window.__hrOpts.sunburst);
      buildChart('echarts-streamgraph',  window.__hrOpts.streamgraph);
      buildChart('echarts-network',      window.__hrOpts.network);
      buildChart('echarts-sankey',       window.__hrOpts.sankey);
    }

    document.addEventListener('DOMContentLoaded', function() {
      if (typeof echarts === 'undefined') {
        document.querySelectorAll('.echarts-chart').forEach(el => {
          el.innerHTML = '<div style="background:#f0f0f0;color:#666;text-align:center;line-height:400px;">Load failed</div>';
        });
        return;
      }
      rebuildAllCharts();
    });
  </script>

</body>
</html>
""")
```

- [ ] **Step 4: 跑 Stage 2 template 测试确认通过**

Run: `uv run pytest tests/test_visualization/test_html_assembler.py::TestStage2TemplateContent -v`
Expected: 4 个测试全绿。

- [ ] **Step 5: 跑全 visualization 测试**

Run: `uv run pytest tests/test_visualization/ -v`
Expected: 大部分绿。 `test_html_assembler.py::TestAssembleHtml` 中的 `test_english_titles_present` 和 `test_assembled_html_has_4_echarts_charts` 仍应通过(英文标题已替换, 4 个 echarts.init 已替换为 1 个 rebuildAllCharts + 4 个 buildChart, 命中 `echarts.init` 字符串)。 其他 Stage 1 集成测试可能因 `echarts.init` 改为只在 rebuildAllCharts 内出现 → `html.count("echarts.init")` 仍 ≥ 1 (rebuildAllCharts 内 4 次)。 调整 `test_assembled_html_has_4_echarts_charts` 的断言为 `>= 4` 应已满足, 验证一下。

- [ ] **Step 6: 验证 template.py 0 中文(除 docstring 注释)**

Run:
```bash
grep -rP '[\x{4e00}-\x{9fff}]' src/tcfd_extractor/visualization/template.py
```
Expected: 无输出(整个 template 100% 英文)。

- [ ] **Step 7: Commit**

```bash
git add src/tcfd_extractor/visualization/template.py tests/test_visualization/test_html_assembler.py
git commit -m "feat(template): Stage 2 — Inter font + Alpine.js + dark default + side panel

- Inter 字体 (Google Fonts, weights 400/500/600/700, display=swap)
- Alpine.js 3.13.5 (defer CDN, store('hrApp') 模式)
- CSS 变量主题: 暗色默认 + [data-theme='light'] 切换
- 主题切换按钮 (header 角标, localStorage hr-theme 持久)
- 4 ECharts 改 rebuildAllCharts + applyTheme + dispose+reinit
- bindClickHandlers: network 节点 / sankey 边 → Alpine.openPanel
- 右侧侧栏 (<aside>) + backdrop + ESC 关闭 + ✕ 按钮
- 全部 section 标题/说明英文化
- 测试: 4 新集成 case (data-theme / Inter / Alpine / side-panel z-index)
"
```

---

## Chunk 4: `html_assembler.py` — `build_context_index()` + 注入 JSON

**Files:**
- Modify: `src/tcfd_extractor/visualization/html_assembler.py`
- Modify: `tests/test_visualization/test_html_assembler.py`

**目标**: 数据装配层 — 注入 `__hrTranslateMap`(全量 KEYWORD_TRANSLATIONS dict)和 `__hrContextIndex`(节点 + sankey 边 → context 列表, 限 3 sample)。 新增 `build_context_index()` 函数, 实现 spec §8 全部行为 (dedup / 3 sample cap / sankey 边索引生成 / 排序 edge key)。

### Task 4.1: 写 `build_context_index()` 失败测试

**Files:**
- Modify: `tests/test_visualization/test_html_assembler.py` (末尾追加)

- [ ] **Step 1: 写 3 个 build_context_index 单元测试**

```python
class TestBuildContextIndex:
    """Spec §8: build_context_index — 关键词索引 / sankey 边索引 / 3 sample cap。"""

    def _make_results(self, tmp_path: Path) -> Path:
        base = tmp_path / "evaluate_cooccurrence"
        year_dir = base / "2023"
        year_dir.mkdir(parents=True)
        records = []
        # 同一关键词 4 次出现, 应 cap 到 3 条
        for i in range(4):
            records.append({
                "file": f"x{i}.md", "keyword_a": "碳交易", "keyword_b": "低碳",
                "context": f"ctx {i}", "is_tcfd_related": True, "dimension": "政策",
            })
        # 第二组, 另一对
        records.append({
            "file": "y.md", "keyword_a": "环保", "keyword_b": "碳市场",
            "context": "ctx env", "is_tcfd_related": True, "dimension": "市场",
        })
        # 不相关 → 不进索引
        records.append({
            "file": "z.md", "keyword_a": "x", "keyword_b": "y",
            "context": "ctx", "is_tcfd_related": False, "dimension": "无",
        })
        (year_dir / "results.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in records),
            encoding="utf-8",
        )
        return base

    def test_keywords_index_caps_at_3_samples(self, tmp_path):
        from tcfd_extractor.visualization.html_assembler import build_context_index
        results = self._make_results(tmp_path)
        index = build_context_index(eval_dir=results, years=[2023])
        # 碳交易/低碳 4 条 → cap 到 3
        assert len(index["keywords"]["碳交易"]) == 3
        assert len(index["keywords"]["低碳"]) == 3

    def test_sankey_index_uses_sorted_edge_key(self, tmp_path):
        from tcfd_extractor.visualization.html_assembler import build_context_index
        results = self._make_results(tmp_path)
        index = build_context_index(eval_dir=results, years=[2023])
        # sankey 边 key: 排序后的 a->b
        assert "碳交易->低碳" in index["sankey"]
        assert "低碳->碳交易" not in index["sankey"]  # 只存正序
        # 第二组: 环保 ↔ 碳市场
        assert "碳市场->环保" in index["sankey"]

    def test_unrelated_records_excluded(self, tmp_path):
        from tcfd_extractor.visualization.html_assembler import build_context_index
        results = self._make_results(tmp_path)
        index = build_context_index(eval_dir=results, years=[2023])
        # is_tcfd_related=False 的 x/y 不进索引
        assert "x" not in index["keywords"]
        assert "y" not in index["keywords"]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/test_visualization/test_html_assembler.py::TestBuildContextIndex -v`
Expected: `ImportError: cannot import name 'build_context_index' from 'tcfd_extractor.visualization.html_assembler'`

### Task 4.2: 实现 `build_context_index()`

**Files:**
- Modify: `src/tcfd_extractor/visualization/html_assembler.py`

- [ ] **Step 3: 添加 `build_context_index` 函数**

在 `src/tcfd_extractor/visualization/html_assembler.py` 顶部 import 区域添加:

```python
from .translations import KEYWORD_TRANSLATIONS, translate_smart
```

在 `assemble_html` 函数前添加 `build_context_index`:

```python
def build_context_index(eval_dir: Path, years: list[int]) -> dict:
    """Build keyword → [context, ...] AND sankey-edge → [context, ...] indexes.

    Spec §8:
    - 同一 record 同时进 2 个索引: 节点 click 和流道 click 都能找到原文
    - 每个关键词/边最多 3 sample (避免注入过大)
    - sankey 边 key 用排序后的 a->b 字符串 (与 click handler 保持一致)
    """
    index: dict = {"keywords": {}, "sankey": {}}
    for year in years:
        jsonl = eval_dir / str(year) / "results.jsonl"
        if not jsonl.exists():
            logger.warning("Context index: year %d jsonl missing at %s", year, jsonl)
            continue
        with jsonl.open(encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not r.get("is_tcfd_related"):
                    continue
                ctx = r.get("context", "").strip()
                if not ctx:
                    continue
                entry = {
                    "id": f"{year}-{r.get('file', '')}-{line_no}",
                    "original": ctx,
                    "translated": translate_smart(ctx),
                    "source": r.get("file", "").split("/")[-1],
                    "year": year,
                    "dimension": r.get("dimension", ""),
                }
                # 关键词索引 (供 network 节点 click)
                for kw in (r.get("keyword_a", ""), r.get("keyword_b", "")):
                    if kw:
                        index["keywords"].setdefault(kw, []).append(entry)
                # Sankey 边索引 (供 sankey 流道 click)
                ka = r.get("keyword_a", "")
                kb = r.get("keyword_b", "")
                if ka and kb:
                    pair = sorted([ka, kb])
                    edge_key = f"{pair[0]}->{pair[1]}"
                    index["sankey"].setdefault(edge_key, []).append(entry)
    # 限制每个关键词/边最多 3 条
    for k in index["keywords"]:
        index["keywords"][k] = index["keywords"][k][:3]
    for k in index["sankey"]:
        index["sankey"][k] = index["sankey"][k][:3]
    return index
```

- [ ] **Step 4: 跑测试确认 build_context_index 通过**

Run: `uv run pytest tests/test_visualization/test_html_assembler.py::TestBuildContextIndex -v`
Expected: 3 个测试全绿。

### Task 4.3: 注入 `__hrTranslateMap` 和 `__hrContextIndex` 到 HTML

**Files:**
- Modify: `src/tcfd_extractor/visualization/html_assembler.py`

- [ ] **Step 5: 写注入集成测试**

在 `tests/test_visualization/test_html_assembler.py` 末尾追加:

```python
class TestContextInjection:
    """Spec §5.3 + §8: 注入 window.__hrTranslateMap 和 window.__hrContextIndex。"""

    def test_translate_map_injected(self, tmp_path):
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            refactor_bar_b64="x",
            module_graph_svg="<svg></svg>",
        )
        assert "window.__hrTranslateMap" in html
        # 含已知英文
        assert "Carbon Trading" in html
        assert "Policy" in html

    def test_context_index_injected(self, tmp_path):
        results = _make_min_results(tmp_path)
        html = assemble_html(
            results_root=results,
            refactor_bar_b64="x",
            module_graph_svg="<svg></svg>",
        )
        assert "window.__hrContextIndex" in html
```

- [ ] **Step 6: 跑测试确认失败**

Run: `uv run pytest tests/test_visualization/test_html_assembler.py::TestContextInjection -v`
Expected: 失败 (assemble_html 尚未注入这两个变量)。

- [ ] **Step 7: 修改 `assemble_html` 调用 build_context_index + 注入 JSON**

修改 `assemble_html` 函数 (替换整段):

```python
def assemble_html(
    results_root: Path,
    *,
    refactor_bar_b64: str,
    module_graph_svg: str,
    refactor_stats: dict | None = None,
    build_date: str | None = None,
) -> str:
    """Load data, build charts, render template. Returns final HTML string.

    Stage 2: 注入 __hrTranslateMap (全量 KEYWORD_TRANSLATIONS) 和
    __hrContextIndex (节点 + sankey 边 → context 列表, 限 3 sample)。
    """
    clusters_dir = Path("output/tcfd_keywords/phase5_category_mapping")
    eval_dir = results_root

    sunburst_opt = build_sunburst(load_sunburst_data(clusters_dir), TCFD_THEME_CONFIG)
    streamgraph_opt = build_streamgraph(
        load_streamgraph_data(eval_dir, years=range(2000, 2025)), TCFD_THEME_CONFIG
    )
    network_opt = build_network(
        load_network_data(eval_dir, years=[2022, 2023, 2024]), TCFD_THEME_CONFIG
    )
    try:
        sankey_opt = build_sankey(load_sankey_data(eval_dir=eval_dir), TCFD_THEME_CONFIG)
    except (FileNotFoundError, KeyError, ValueError) as e:
        logger.warning("Sankey: load_sankey_data failed (%s: %s), rendering empty sankey",
                       type(e).__name__, e)
        sankey_opt = {"series": [{"type": "sankey", "data": [], "links": []}]}

    # 4 个 option 序列化为 JSON 字符串
    sunburst_json = _json.dumps(sunburst_opt, ensure_ascii=False)
    streamgraph_json = _json.dumps(streamgraph_opt, ensure_ascii=False)
    network_json = _json.dumps(network_opt, ensure_ascii=False)
    sankey_json = _json.dumps(sankey_opt, ensure_ascii=False)

    # Stage 2: 注入 context 索引 (与 load_network_data 的 years 参数一致)
    context_index = build_context_index(eval_dir=eval_dir, years=[2022, 2023, 2024])
    context_index_json = _json.dumps(context_index, ensure_ascii=False)
    translate_map_json = _json.dumps(KEYWORD_TRANSLATIONS, ensure_ascii=False)

    return HTML_TEMPLATE.render(
        sunburst_json=sunburst_json,
        streamgraph_json=streamgraph_json,
        network_json=network_json,
        sankey_json=sankey_json,
        refactor_b64=refactor_bar_b64,
        module_graph_svg=module_graph_svg,
        refactor_stats=refactor_stats or {},
        build_date=build_date or date.today().isoformat(),
        # Stage 2 注入
        translate_map_json=translate_map_json,
        context_index_json=context_index_json,
    )
```

- [ ] **Step 8: 跑注入测试确认通过**

Run: `uv run pytest tests/test_visualization/test_html_assembler.py::TestContextInjection -v`
Expected: 2 个测试全绿。

- [ ] **Step 9: 跑全 visualization 测试套件**

Run: `uv run pytest tests/test_visualization/ -v`
Expected: 全绿。 Stage 1 全部原 case (含 `test_english_titles_present` / `test_assembled_html_has_4_echarts_charts` / `test_kpis_appear_in_html`) 仍通过。

- [ ] **Step 10: Commit**

```bash
git add src/tcfd_extractor/visualization/html_assembler.py tests/test_visualization/test_html_assembler.py
git commit -m "feat(html_assembler): Stage 2 — build_context_index() + 注入 translate_map + context_index

- 新增 build_context_index(eval_dir, years): 节点 + sankey 边 → context 列表
- 每个关键词/边限 3 sample (避免注入过大)
- sankey 边 key 用排序后的 a->b 字符串 (与 click handler 保持一致)
- 注入 window.__hrTranslateMap (全量 KEYWORD_TRANSLATIONS JSON)
- 注入 window.__hrContextIndex (节点 + sankey 索引 JSON)
- 注入位置: <head> 中 ECharts CDN 之后, Alpine <script defer> 之前
- 测试: 5 新 case (build_context_index 3 + 注入 2)
"
```

---

## Chunk 5: 端到端构建 + 部署 + 视觉验证

**Files:**
- 无源码改动
- 重建: `output/hr_report/index.html`
- Force-push: `output/hr_report` 独立 deploy repo

**目标**: 把 Stage 2 全部代码改动串起来, 跑 build 脚本, 验证 HTML 体积/泄漏检查/视觉 7 项/部署 200。

### Task 5.1: 跑 build 脚本

- [ ] **Step 1: 清掉旧的 output/hr_report**

Run: `rm -rf /home/bo/projects/python/frequency_analyzer/output/hr_report/*`
注意: 保留 `output/hr_report/.git` (它是独立 deploy repo), 但清掉 index.html / README.md / .nojekyll。 实际上 `scripts/build_hr_report.py` 会 overwrite, 直接跑即可, 但为干净起见先 rm。

更安全的写法:
```bash
cd /home/bo/projects/python/frequency_analyzer
rm -f output/hr_report/index.html output/hr_report/README.md
# 保留 .git 和 .nojekyll
```

- [ ] **Step 2: 跑 build_hr_report.py**

Run: `uv run python scripts/build_hr_report.py --output output/hr_report/`
Expected: 退出码 0, 打印 `Wrote output/hr_report/index.html (NNN,NNN chars)`, 泄漏检查通过, `Build complete`。

如果失败, 排查:
- 数据缺失 (e.g., `output/evaluate_cooccurrence/{2022,2023,2024}/results.jsonl`) — 用上一轮部署的 git tag 拉回
- 模板渲染错误 — 检查 `template.py` Jinja 语法
- 泄漏检查失败 — 跑 `python scripts/check_leakage.py output/hr_report/index.html` 详细输出

- [ ] **Step 3: 验证 HTML 体积 (spec §13 验证清单 wc -c 介于 2.5MB-3.5MB)**

Run: `wc -c output/hr_report/index.html`
Expected: 介于 2,500,000 - 3,500,000 bytes (2.5-3.5MB)。 Stage 1 是 1.5-2MB, 增量为 context 索引 ~1MB。 如果 < 2.5MB, 检查 context_index 是否实际有内容 (debug: 临时 dump 到文件看大小)。 如果 > 3.5MB, spec §8 已规划 3-2-1 降级路径, 需在 `assemble_html` 注入前加 size check (本 spec 已要求 `logger.warning` 强制输出)。

注意: spec §8 要求**实施时先 dry-run 测一次大小**, 超过 3MB 降到 2 sample。 实施时如 `len(context_index_json) > 3*1024*1024` 触发降级。 这是 defensive coding, 留待真实数据测出来再决定是否触发 — 实施时按 3 sample 跑一次, 测得体积再调整。

- [ ] **Step 4: 跑全测试套件最终确认**

Run: `uv run pytest tests/test_visualization/ -v`
Expected: 全绿。 含 Stage 1 全部原 case + Stage 2 新增 case (Chunk 1: 5+39+1=45 case; Chunk 2: 4+5+4=13 case; Chunk 3: 4 case; Chunk 4: 3+2=5 case, 总新增 ≥ 16 case)。

- [ ] **Step 5: 跑泄漏检查独立验证**

Run: `python scripts/check_leakage.py output/hr_report/index.html`
Expected: 退出码 0。

### Task 5.2: 部署到 GitHub Pages

- [ ] **Step 6: 进入 output/hr_report (独立 deploy repo)**

Run: `cd output/hr_report && git status`
Expected: `Changes not staged for commit: modified: index.html` (+ README.md 也许 modified)。

- [ ] **Step 7: Stage + commit**

```bash
cd output/hr_report
git add -A
git -c user.email="noreply@github.com" -c user.name="somAzzz" commit -m "feat: Stage 2 — UI/UX dark + Inter + Alpine side panel (中→英)"
```

- [ ] **Step 8: Push (force, 单一来源)**

```bash
cd output/hr_report
git push upstream main --force
```

Expected: `remote: Create a pull request for 'main'...` 或 `To https://github.com/somAzzz/tcfd-report.git\n + abcdef..123456 main -> main` 之类的成功信息。

### Task 5.3: 视觉验证 (远程 + 本地)

- [ ] **Step 9: 远程 HTTP 200**

Run: `curl -sI https://somAzzz.github.io/tcfd-report/ | head -1`
Expected: `HTTP/2 200`

- [ ] **Step 10: 远程 7 项客观检查 (WebFetch) (spec §13 7 项)**

对 `https://somAzzz.github.io/tcfd-report/` 跑 WebFetch, 验证:

(a) **暗色默认**: HTML 顶部 `<html data-theme="dark">` 出现, body background `#0f1419`
(b) **主题切换按钮**: 出现 `hr-theme-toggle` class + `@click="$store.hrApp.toggleTheme()"`
(c) **Inter 字体**: `<link>` 含 `Inter:wght@400;500;600;700&display=swap`
(d) **全英文**: grep `[\u4e00-\u9fff]` 命中 = 0 (除 `[[ZH: ...]]` 降级占位)
(e) **Network click handler**: 出现 `echarts-network` + `params.dataType === 'node'` + `Alpine.store('hrApp').openPanel`
(f) **Sankey click handler**: 出现 `echarts-sankey` + `params.dataType === 'edge'` + 排序后 edge key
(g) **侧栏关闭 3 种方式**: `closePanel` 在 (1) `✕` 按钮 `@click` (2) `@keydown.escape.window` (3) backdrop `@click` 3 处出现

如果 (e)/(f) 的 edge key 不匹配 (reviewer 反馈过的 bug) — 回到 Chunk 3 template.py 的 `bindClickHandlers` 函数, 确认 `const pair = [source, target].sort(); const edgeKey = \`${pair[0]}->${pair[1]}\`;` 与 build_context_index 中的 `pair = sorted([ka, kb])` 一致。

- [ ] **Step 11: 验证清单硬指标 (spec §13)**

```bash
# 1. echarts.py 中文命中 ≤ 5 (仅 docstring)
grep -P '[\x{4e00}-\x{9fff}]' src/tcfd_extractor/visualization/echarts.py | wc -l
# Expected: <= 5

# 2. template.py 中文命中 = 0
grep -P '[\x{4e00}-\x{9fff}]' src/tcfd_extractor/visualization/template.py | wc -l
# Expected: 0

# 3. data-theme="dark" 命中 1
grep -c 'data-theme="dark"' output/hr_report/index.html
# Expected: 1

# 4. Inter:wght 命中 1
grep -c "Inter:wght" output/hr_report/index.html
# Expected: 1

# 5. alpinejs 命中 1
grep -c "alpinejs" output/hr_report/index.html
# Expected: 1

# 6. __hrTranslate 命中 ≥ 5
grep -c "__hrTranslate" output/hr_report/index.html
# Expected: >= 5

# 7. __hrContextIndex 命中 1
grep -c "__hrContextIndex" output/hr_report/index.html
# Expected: 1

# 8. HTML 体积
wc -c output/hr_report/index.html
# Expected: 2.5MB-3.5MB (2500000-3500000 bytes)

# 9. 泄漏检查
python scripts/check_leakage.py output/hr_report/index.html
# Expected: 退出码 0
```

- [ ] **Step 12: 最终 commit (主仓元数据更新)**

```bash
cd /home/bo/projects/python/frequency_analyzer
git status
# Should be clean (output/hr_report 已在独立 repo commit 过, 主仓 .gitignore 排除)
```

确认主仓无 pending 改动。 实施计划全部 commit 在主仓 Chunk 1-4 (4 个 commits), output/hr_report 1 个 commit。

- [ ] **Step 13: 报告完成**

向用户报告:
- Stage 2 部署完成, 4 个主仓 commits + 1 个 deploy repo commit
- 验证清单 13 项全绿
- URL: https://somAzzz.github.io/tcfd-report/
- 测试统计: Stage 1 原 ~18 case + Stage 2 新增 ≥ 16 case = ≥ 34 case
- HTML 体积: N.NN MB (在 2.5-3.5MB 范围)
- 已知限制: 浏览器必须支持 ES2017+ (Alpine 3 + ECharts 5)

---

## 关键风险 & 缓解

| 风险 | 触发 | 缓解 |
|---|---|---|
| context 索引 > 3MB | 大数据量 (3 年 × 5000 行) | spec §8 已规划 3-2-1 降级路径, `logger.warning` 强制输出 |
| `data_loader.py` 改 category 破坏 Stage 1 测试 | Task 2.3.2 | 同步修改 `test_data_loader.py` 英文 category 断言, 跑全测试验证 |
| template.py Jinja 转义 `{{ x|safe }}` 注入 JSON | 转义错 | `\|safe` filter 保留, 配合 `ensure_ascii=False` JSON dump, 已验证 Stage 1 模式 |
| Alpine store 顺序: Alpine <script defer> 在 store 注册后 | Alpine 启动时序 | `x-init` 内的 `Alpine.store('hrApp', ...)` 在 Alpine.start() 期间执行, defer + x-init 是 Alpine 官方推荐模式 |
| ECharts dispose 后 click 监听器未清理 | 主题切换反复 dispose+reinit | ECharts dispose() 自动解绑所有 listener (Stage 1 验证过) |
| edge key 排序不一致 | build_context_index 用 sort, click handler 不用 | 已在 spec §7.2 reviewer 反馈中标记, Chunk 3 template.py Step 3 已显式 `const pair = [source, target].sort();` |
| `display=swap` 字体加载慢 | Google Fonts CDN 不稳定 | 不阻塞, system-ui fallback, 加载完后平滑替换 (spec §4 决策) |
