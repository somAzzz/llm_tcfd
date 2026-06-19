# Stage 2 — UI/UX 升级 + 全英文化设计 Spec

**日期**: 2026-06-19
**作者**: 头脑风暴会话 (Stage 2)
**状态**: 待 spec 审阅
**前置**: Stage 1 spec (`2026-06-18-echarts-visualization-upgrade-design.md`) 已完成并部署, 4 个 ECharts 图表 (sunburst / streamgraph / network / sankey) 已上线 `https://somAzzz.github.io/tcfd-report/`

## 0. 背景与上下文

Stage 1 完成了从 Plotly 到 ECharts 的迁移和 4 个高级交互图的部署。 Stage 2 聚焦 UI/UX 收尾和全英文化, 让报告成为可对外展示的"国际化工程作品"。

**头脑风暴期间锁定的 6 项决策**:

1. **翻译范围**: UI 标题/说明 + 维度名 (政策/市场/技术) + 数据关键词 (经 `translations.py` 词典) — 全部替换为英文
2. **暗色模式**: 暗色为默认, 手动切换 (header 角标), localStorage 持久化
3. **Alpine.js 应用范围**: 仅用于暗色切换状态 + 点击侧边栏面板状态; Hover 仍由 ECharts 原生 tooltip 处理 (避免 Alpine DOM 抖动掉帧)
4. **Tooltip 数据源**: 复用 results.jsonl 已有 `context` 字段 (年报原文片段), 不重新跑 LLM
5. **翻译降级**: `translate_smart()` 函数, 词典命中 → 英文; 纯 ASCII → 保留; 其它 → `[[ZH: xxx]]` 包裹 (调试可见)
6. **数据流分层**: `data_loader.py` 保留中文原值 (不动 snapshot 测试), 翻译在 `echarts.py` builder 和 `template.py` 显示层完成

## 1. 目标

将 Stage 1 部署的 ECharts 报告 (中英混合, 亮色, 单一字体) 升级为:

- **全英文**: 标题/说明/维度名/关键词全部英文 (中文仅在 `[[ZH: xxx]]` fallback 时短暂出现)
- **暗色优先**: 暗色为默认主题, 浅色可手动切换, localStorage 持久
- **精致排版**: Inter 字体 (Google Fonts), 优化留白, KPI 卡片视觉层次
- **点击深度**: 关键词节点 / Sankey 流道点击后弹出右侧侧栏, 显示原文 context (中英对照)

**非目标** (避免范围蔓延):
- 不引入 npm/webpack/构建工具 (保持单文件 HTML)
- 不重跑任何数据流水线 (沿用 Stage 1 的 JSONL + 聚类结果)
- 不改 GitHub Pages 部署流程
- 不实现 i18n 多语言切换框架 (本次只是中→英, 单一目标语言)
- 不实现 LLM 重新提取新 snippet (沿用已有 `context` 字段)
- 不把 Mermaid 模块图换成 ECharts (Stage 1 已确认保留 Mermaid)

## 2. 架构

```
                        输出数据源 (Stage 1 已有, 不动)
  output/evaluate_cooccurrence/{2022,2023,2024}/results.jsonl  ← context 字段复用
  output/tcfd_keywords/phase5_category_mapping/*_clusters.json
  output/tcfd_keywords/tcfd_keywords_summary.csv
                          │
                          ▼
  data_loader.py [ZERO 改动]  ← 保留中文原值
                          │
                          ▼
  translations.py [扩展]
    ├─ KEYWORD_TRANSLATIONS  ← 追加 dim 名 / cluster label / UI 术语
    ├─ translate()          ← 保留 (精确匹配)
    └─ translate_smart()    ← 新增 (带降级 fallback)
                          │
                          ▼
  echarts.py [修改]
    ├─ _t(kw)               ← 新增内部 helper, 统一走 translate_smart()
    ├─ 4 个 builder         ← 标题/副标题/axis/formatter 全部英文化 + 走 _t()
    └─ TCFD_THEME_CONFIG    ← 调整 color palette (暗色友好) + 字号 + 字体
                          │
                          ▼
  template.py [重写]
    ├─ <head>
    │   ├─ <link> Inter Google Fonts (400/500/600/700)
    │   ├─ <script defer> Alpine.js v3.x CDN
    │   ├─ ECharts CDN (沿用 Stage 1, 已在 head)
    │   └─ <style> CSS 变量主题 (暗色默认, 浅色 [data-theme="light"])
    ├─ <body x-data="{ theme: 'dark', panel: null }">
    │   ├─ header [加 🌙/☀️ 切换按钮]
    │   ├─ KPI 卡片 [4 个, 大字号 Inter 700]
    │   ├─ 4 个 section [纯英文说明 + 图表]
    │   └─ <aside x-show="panel" x-transition>  ← Alpine 侧栏
    └─ <script> ECharts init + chart.on('click') 联动 Alpine
                          │
                          ▼
  output/report/index.html (单文件, ~1.5-2MB)
```

**核心约束**:
- 单文件 HTML, 全部内联
- 翻译在显示层 (`echarts.py` + `template.py`), 数据层 (`data_loader.py`) 不动
- Alpine.js 仅托管低频状态 (toggle, panel), ECharts 自管高频 hover

## 3. 文件结构 (改动一览)

| 文件 | 操作 | 责任 |
|---|---|---|
| `src/tcfd_extractor/visualization/translations.py` | **扩展** | 新增 `translate_smart()` + 词典扩展 (~30 个新条目) |
| `src/tcfd_extractor/visualization/echarts.py` | **修改** | (a) 引入 `_t()` helper; (b) 4 个 builder 全部英文化; (c) `TCFD_THEME_CONFIG` 调色板 + 字号 |
| `src/tcfd_extractor/visualization/template.py` **重写** | **大改** | (a) Inter 字体 + CSS 变量主题; (b) Alpine.js `<script defer>`; (c) header 加暗色切换; (d) KPI 卡片样式升级; (e) 全部说明文字英文化; (f) 加 `<aside>` 侧栏容器 + Alpine 状态; (g) ECharts init 后加 `chart.on('click', ...)` 联动 Alpine |
| `src/tcfd_extractor/visualization/html_assembler.py` | **小改** | (a) 注入 `__context_index` JSON (节点/边 → context 列表); (b) 注入 `__keyword_translator` 简化版 (模板直接调) |
| `src/tcfd_extractor/visualization/data_loader.py` | **不改** | 保留 Stage 1 行为, 中文原值 |
| `tests/test_visualization/test_translations.py` | **扩展** | 新增 `test_translate_smart_*` 5 case |
| `tests/test_visualization/test_echarts.py` | **扩展** | 4 个 builder 标题/副标题为英文的断言 |
| `tests/test_visualization/test_data_loader.py` | **不改** | Stage 1 测试不动 (中文原值不变) |
| `scripts/build_report.py` | **不改** | 沿用 |

**新建 0 + 扩展 2 + 修改 3 + 不改 3** = 5 个文件改动 + 0 个文件新建 (本次主要是模板层).

## 4. 主题系统设计 (CSS 变量)

### 4.1 `data-theme` 切换

```html
<html data-theme="dark">  <!-- 默认暗色 -->
  <body>
    <button @click="theme = theme === 'dark' ? 'light' : 'dark';
                    localStorage.setItem('hr-theme', theme);
                    document.documentElement.dataset.theme = theme">
      <span x-show="theme === 'dark'">☀️</span>
      <span x-show="theme === 'light'">🌙</span>
    </button>
  </body>
</html>
```

localStorage key: `hr-theme`, 值 `'dark'` | `'light'`. 首次访问默认 `dark`, 后续读 localStorage.

### 4.2 CSS 变量定义 (template.py `<style>`)

```css
:root[data-theme="dark"] {
  --bg: #0f1419;            /* near-black, 蓝灰调 */
  --fg: #e6e6e6;
  --card-bg: #1a1f24;
  --card-border: #2a2f34;
  --muted: #8b95a1;
  --accent: #58a6ff;        /* GitHub 风格的亮蓝 */
  --accent-fg: #ffffff;
  --header-bg: linear-gradient(135deg, #1f3a5f 0%, #1a4d2e 100%);  /* 暗色下降低饱和 */
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

/* 全局过渡: 主题切换时颜色平滑 (避免突兀跳变) */
body, section, .kpi-card, header, .hr-side-panel, .callout {
  transition: background-color 0.25s ease, color 0.25s ease,
              border-color 0.25s ease;
}
```

**ECharts 主题联动**: 通过 JS 在 `chart.setOption()` 前读取 `document.documentElement.dataset.theme`, 动态调整 option 中的 `textStyle.color` / `axisLine.lineStyle.color` / `splitLine.lineStyle.color`. 见 §6.

## 5. 翻译系统设计 (`translations.py` 扩展)

### 5.1 `translate_smart()` 新增

```python
import re

_NON_ALNUM_RE = re.compile(r"[^\w\s]+", re.UNICODE)


def translate_smart(keyword: str) -> str:
    """Smart translate with graceful fallback.

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

### 5.2 词典扩展 (新增条目, 写入 `KEYWORD_TRANSLATIONS`)

```python
# 维度名
"政策": "Policy",
"市场": "Market",
"技术": "Technology",
"无": "N/A",  # 无维度 (N/A 显式优于 "None", 避免与 Python None 混淆)

# 聚类 math_label
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
"披露": "Disclosure",
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

**降级标记统一**: `translate()` 和 `translate_smart()` 都使用 `[[ZH: xxx]]` (双中括号) 作为降级标记, 与现有 `translations.py:148` 的 `[ZH: ...]` (单中括号) 不一致 — 改 `translate()` 也用 `[[ZH: xxx]]` 以统一, 避免未来阅读混淆.

### 5.3 翻译注入点

| 位置 | 翻译内容 | 实现方式 |
|---|---|---|
| `echarts.py` 各 builder | chart title / subtitle / axis label / legend | 直接硬编码英文 (避免运行时查表性能开销) |
| `echarts.py` tooltip formatter | 节点名 / 维度名 / 频次 | `formatter: "function(p) { return window.__hrTranslate(p.name) + ' (' + p.value + ' occurrences)'; }"` |
| `echarts.py` sankey label formatter | 节点名剥离 stage{N}_ 前缀 + 翻译 | 沿用 Stage 1, formatter 内调用 `window.__hrTranslate` (降级回退 `(s => s)`) |
| `template.py` 静态文本 | header / sections / captions / Mermaid | 直接写英文 |
| `template.py` 侧栏模板 | 标题 / 维度徽章 | Alpine 模板表达式 `x-text="panel.dimension ? window.__hrTranslate(panel.dimension) : ''"` |
| `html_assembler.py` 注入 | `window.__hrTranslate` + `window.__hrContextIndex` | **注入位置**: `<head>` 中, ECharts CDN 之后, Alpine `<script defer>` 之前 (确保两个 consumer 都能找到) |

**`__hrTranslate` 注入定义** (html_assembler.py 注入, ~3KB inline `<script>`):

```javascript
window.__hrTranslate = function(keyword) {
  // 客户端兜底: 服务端 Python 端应该已经把所有 display-facing 字符串翻译好了
  // 客户端只对运行时动态值 (ECharts 回调里取出的 p.name) 做兜底翻译
  if (!keyword) return '';
  const map = window.__hrTranslateMap || {};
  if (map[keyword]) return map[keyword];
  if (/^[\x00-\x7F]+$/.test(keyword)) return keyword;  // 纯 ASCII
  return '[[ZH: ' + keyword.replace(/[^\w\s]+/g, '').trim() + ']]';
};
```

**`__hrTranslateMap` 来源**: `html_assembler.py` 把 `KEYWORD_TRANSLATIONS` 全量 dict dump 成 JSON 注入到 `window.__hrTranslateMap` (约 6KB 压缩后 ~3KB). 客户端查表; 命中率 100% 的话零降级. 命中率低时降级走 `[[ZH: xxx]]`.

## 6. ECharts 暗色主题适配

### 6.1 主题切换策略: dispose + reinit (committed)

ECharts 主题切换采用 **dispose + reinit** 方案, **不用 patch**:

**理由**:
- patch 路径需要深拷贝 + 大量字段判断, 容易遗漏 (sunburst 内部样式, sankey 边色等)
- dispose+reinit 200ms 内完成, 用户感知不到
- 简单稳定, 100% 复用 init 时的同一份 code path

**`rebuildAllCharts()` 完整实现** (template.py 内联 `<script>`):

```javascript
// 全局 chart 实例缓存
window.__hrCharts = {};

function buildChart(chartId, opt) {
  const el = document.getElementById(chartId);
  if (!el) return;
  // 销毁旧实例 (如果存在)
  if (window.__hrCharts[chartId]) {
    window.__hrCharts[chartId].dispose();
  }
  // 应用主题 (调色板已硬编码, 只调 text/axis 颜色)
  opt = applyTheme(opt, document.documentElement.dataset.theme);
  // 新建
  const chart = echarts.init(el);
  chart.setOption(opt);
  window.__hrCharts[chartId] = chart;
  // 绑定 click → Alpine panel
  bindClickHandlers(chart, chartId);
  return chart;
}

function rebuildAllCharts() {
  buildChart('echarts-sunburst',     window.__hrOpts.sunburst);
  buildChart('echarts-streamgraph',  window.__hrOpts.streamgraph);
  buildChart('echarts-network',      window.__hrOpts.network);
  buildChart('echarts-sankey',       window.__hrOpts.sankey);
}

function applyTheme(opt, theme) {
  const isDark = theme === 'dark';
  const fg = isDark ? '#e6e6e6' : '#222';
  const muted = isDark ? '#8b95a1' : '#666';
  opt = JSON.parse(JSON.stringify(opt));  // 深拷贝避免污染原 opt
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

// init: 把服务端注入的 4 个 opt 存到全局, 然后首次构建
document.addEventListener('DOMContentLoaded', function() {
  if (typeof echarts === 'undefined') {
    document.querySelectorAll('.echarts-chart').forEach(el => {
      el.innerHTML = '<div style="background:#f0f0f0;color:#666;text-align:center;line-height:400px;">Load failed</div>';
    });
    return;
  }
  window.__hrOpts = {
    sunburst:    {{ sunburst_json|safe }},
    streamgraph: {{ streamgraph_json|safe }},
    network:     {{ network_json|safe }},
    sankey:      {{ sankey_json|safe }},
  };
  rebuildAllCharts();
});
```

**`bindClickHandlers(chart, chartId)`** (template.py 同样内联):

```javascript
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
      // Sankey edge: source/target 在 stage{N}_ 命名空间, 翻译需用 post-formatter 名
      const stripPrefix = s => (s || '').replace(/^stage\d+_/, '');
      const source = stripPrefix(params.data.source);
      const target = stripPrefix(params.data.target);
      const edgeKey = `${source}->${target}`;
      const contexts = (window.__hrContextIndex.sankey[edgeKey] || []).slice(0, 3);
      window.Alpine.store('hrApp').openPanel({
        type: 'link',
        title: `${window.__hrTranslate(source)} → ${window.__hrTranslate(target)}`,
        contexts: contexts,
      });
    }
    // 其它点击 (e.g., 非数据区) → 不响应, panel 保持当前状态
  });
}
```

### 6.2 颜色调色板 (暗色友好)

```python
TCFD_THEME_CONFIG = {
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

> Stage 1 留的"Stage 2 视觉升级仅改此处"注释 → 兑现.

## 7. Alpine.js 应用范围 (动静分离)

### 7.1 Alpine store 注册 (`<head>` + body 入口)

**Alpine 集成模式 (committed)**: 用 **Alpine.store** (而非 inline `x-data`), 在 `Alpine.start()` 之前注册全局 store. 优点: 跨组件共享状态, ECharts `chart.on('click')` 回调通过 `window.Alpine.store('hrApp')` 访问, 避免脆弱的 DOM 查询 (`document.querySelector('[x-data]').__x.$data`).

**Alpine CDN URL (locked)**: `https://cdn.jsdelivr.net/npm/alpinejs@3.13.5/dist/cdn.min.js` (defer load, ~15KB gzipped, MIT license, 锁版本). Validation: `grep -c "alpinejs@3.13" output/report/index.html` 命中 1.

**Inter 字体 CDN URL (locked)**: `https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap` — `display=swap` 避免 FOIT, 字体加载失败时回退到 system-ui, 加载完后平滑替换.

```html
<head>
  ...
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
  <script>
    // 注入: 翻译 map + context 索引 (由 html_assembler.py 渲染)
    window.__hrTranslateMap = {{ translate_map_json|safe }};
    window.__hrContextIndex = {{ context_index_json|safe }};
    window.__hrTranslate = function(kw) { /* 见 §5.3 */ };
  </script>
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.13.5/dist/cdn.min.js"></script>
</head>
<body x-data
      x-init="
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
```

### 7.2 ECharts → Alpine 联动 (click)

**Escape hatch 定义** (你提的 §2.1 / §9 风险):

1. **re-bind after dispose**: `buildChart()` 每次都调 `bindClickHandlers()`, 旧 chart `dispose()` 后 click 监听器自动失效, 新 chart 重新绑定. 不需要手动 `off()`.
2. **非数据区点击**: 只匹配 `params.dataType === 'node'` / `'edge'`. 其它 (`'axisLabel'` / `'legend'` / 空白) 不响应, panel 保持当前状态 (不关闭). 这给用户"误点可恢复"的安全感.
3. **Event delegation**: 每个 chartId 一个独立 handler, 在 `bindClickHandlers(chart, chartId)` 内 `if/else if` 分发. 不全局委托, 避免误捕.

```javascript
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
      // Sankey edge: source/target 在 stage{N}_ 命名空间, 翻译需用 post-formatter 名
      const stripPrefix = s => (s || '').replace(/^stage\d+_/, '');
      const source = stripPrefix(params.data.source);
      const target = stripPrefix(params.data.target);
      // 关键: 与 §8 build_context_index 保持一致 — 排序后的 a->b 字符串
      // 否则 click 永远 miss (reviewer 反馈)
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
```

**Hover 仍由 ECharts 原生 tooltip 处理** (不经过 Alpine), 避免 DOM 抖动掉帧 (你的 §2.1 反馈).

### 7.3 侧栏 UI (含 backdrop 关闭 + z-index)

```html
<!-- Backdrop: 点击关闭侧栏 -->
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
```

**关闭侧栏的 3 种方式** (验证清单 §13(g) 完整覆盖):
1. ✕ 按钮: `@click="$store.hrApp.closePanel()"`
2. ESC 键: `@keydown.escape.window="$store.hrApp.closePanel()"`
3. 点击 backdrop: `div.hr-side-panel-backdrop` 的 `@click="$store.hrApp.closePanel()"`

**z-index 层次**: backdrop `z-index: 999`, side-panel `z-index: 1000` — panel 在 backdrop 之上, 都在图表 (默认 z-index auto) 之上.

## 8. context 索引注入 (`html_assembler.py`)

为支持点击侧栏, 需在 HTML 中注入节点→context 的反向索引 (按 `years` 显式参数, 与 `load_network_data(years=[...])` 一致):

```python
def build_context_index(eval_dir, years: list[int]) -> dict:
    """Build keyword → [context, ...] AND sankey-edge → [context, ...] indexes.

    同一 record 同时进 2 个索引: 节点 click 和流道 click 都能找到原文.
    每个关键词/边最多 3 sample (避免注入过大).
    """
    index = {"keywords": {}, "sankey": {}}
    for year in years:
        jsonl = eval_dir / str(year) / "results.jsonl"
        if not jsonl.exists():
            continue
        with jsonl.open(encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                r = json.loads(line)
                if not r.get("is_tcfd_related"):
                    continue
                ctx = r.get("context", "").strip()
                if not ctx:
                    continue
                entry = {
                    "id": f"{year}-{r.get('file','')}-{line_no}",  # 用 (year, file, line_no) 保证唯一且可测试
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
                # Sankey 边索引 (供 sankey 流道 click, 边 key 用剥离 stage{N}_ 后的原始 kw 对)
                ka = r.get("keyword_a", "")
                kb = r.get("keyword_b", "")
                if ka and kb:
                    # edge_key 与 §7.2 click handler 保持一致: 排序后的 a->b
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

**调用方签名** (html_assembler.py 中):

```python
# 沿用 load_network_data 的 years 参数, 保持一致
context_index = build_context_index(eval_dir=results_root, years=[2022, 2023, 2024])
# 注入到模板
return HTML_TEMPLATE.render(
    ...,
    translate_map_json=json.dumps(KEYWORD_TRANSLATIONS, ensure_ascii=False),
    context_index_json=json.dumps(context_index, ensure_ascii=False),
    ...,
)
```

**注入方式**: `<script>window.__hrContextIndex = {...};</script>` 放在 `<head>` ECharts CDN 之后, Alpine `<script defer>` 之前 (与 §7.1 锁定的注入顺序一致).

**体积估算 (修订)**: 原始估算 "1.5MB" 未考虑 JSON wrapper 开销. 修正:
- 3 年 × ~5000 行 × 2 关键词 × 50 char 原文 + ~100 字节 JSON wrapper = ~3MB raw
- 加 sankey 索引 (~1MB) = 总 ~4MB (raw)
- 加 3 sample 限制 + 压缩后注入 ~2.0-2.5MB (经 gzip 后)

**风险**: 接近 3.5MB 验证上限. 实施时先 dry-run 测一次大小, 超过 3MB 则降到 2 sample; 仍超 1 sample; 最坏情况放弃 sankey 索引 (只保留 keywords, sankey 点击显示 "No context available").

**Hard-fail log line**: 任一降级路径触发时, `html_assembler.py` 强制 `logger.warning(...)` 输出:
- 3 sample → 2 sample: `"Sankey context index > 3MB, reducing to 2 sample per keyword"`
- 2 sample → 1 sample: `"Sankey context index > 3MB, reducing to 1 sample per keyword"`
- 1 sample → 放弃 sankey: `"Sankey context index > 3MB even at 1 sample, DROPPING sankey index, only keywords will show context"`

这样部署后用户能从 build log 看到哪条降级路径生效, 便于追踪 HTML 体积异常.

## 9. 关键决策

| 决策 | 选择 | 理由 |
|---|---|---|
| 暗色默认 | 是 | 你的 §1.1 决策 |
| 翻译层位置 | echarts.py + template.py (显示层) | data_loader.py 保留中文, 不破坏 snapshot 测试 (你的 §2.2 反馈) |
| Alpine.js 应用范围 | 仅 toggle + panel (低频) | 避免 hover 高频 Alpine DOM 抖动掉帧 (你的 §2.1 反馈) |
| Tooltip 架构 | ECharts 原生 (hover) + Alpine 侧栏 (click) | 动静分离 (你的 §2.1 反馈) |
| 翻译降级 | `[[ZH: xxx]]` 包裹 | 调试可见, 不静默丢失 |
| `translate()` vs `translate_smart()` | 新增 `translate_smart()`, 保留 `translate()` | 向后兼容 (snapshot test 用 `translate()`) |
| Inter 字体 | Google Fonts CDN, weights 400/500/600/700 | 工程业界标准, 加载快 |
| ECharts 主题切换 | dispose + reinit | 比 patch 简单稳定, 200ms 内完成 |
| 侧栏位置 | 右侧 (right: 0) | 不遮挡主流向 (左到右阅读) |
| 侧栏宽度 | 420px | 长 context 片段可读, 不挤占图表 |
| context 索引体积 | 每关键词限 3 sample | 注入 ~1.5MB, 总 HTML 控制在 3MB 内 |
| Sankey 阶段 4 标签 | 沿用 Stage 1 formatter + `__hrTranslate` | 保持剥离 stage{N}_ 前缀 |
| Mermaid 模块图 | 保留 | Stage 1 决策, 不改 |
| Worktree | 不使用 | 与 Stage 1 一致 |

## 10. 错误处理

| 失败点 | 检测 | 处理 |
|---|---|---|
| 切换主题后 ECharts dispose 异常 | try/catch 包裹 dispose | log warning, 继续重建 |
| context 索引注入过大 (>5MB) | 注入前检查大小 | log warning, 截断每关键词到 1 sample |
| `translate_smart()` 异常输入 (None, bytes) | type check | 返回原值, log warning |
| Alpine.js CDN 加载失败 | window.Alpine 检查 | 降级: 暗色切换按钮 fallback 到原生 JS (`document.documentElement.dataset.theme = ...`) |
| ECharts CDN 失败 (Stage 1 已修) | echarts undefined 检查 | 灰底 + "Load failed" (Stage 1 沿用) |
| Google Fonts 加载慢 | 不阻塞 (display=swap) | 字体先用 system-ui, Inter 加载完自动替换 |
| 点击 Sankey 边时 source/target 未在索引中 | 索引 lookup 容错 | panel 显示 "No context available" |
| 切换主题时当前 panel 未关闭 | Alpine 状态不重置 | panel 数据保留, 但视觉效果不冲突 (侧栏 z-index 高于图表) |

## 11. 测试

| 测试类型 | 覆盖 | 数量目标 |
|---|---|---|
| 单元 (`test_translations.py`) | `translate_smart()` 4 case: 精确命中 / 纯 ASCII / 中文未命中 / 空字符串 | 4 test |
| 单元 (`test_translations.py`) | 词典扩展条目存在性: dim 名 / cluster / UI 术语 / Sankey 阶段 | 1 parametrized test (~10 case) |
| 单元 (`test_echarts.py`) | 4 个 builder 标题/副标题为英文 (含 "TCFD", "Drill", "Zoom" 等关键词) | 4 test |
| 单元 (`test_echarts.py`) | `_t()` helper: 命中词典 / 纯 ASCII / `[[ZH: xxx]]` 包裹 (含空字符串边界) | 4 test |
| 单元 (`test_html_assembler.py`) | `build_context_index()` 自身: 关键词索引 dedup / 3-sample cap / sankey 边索引生成 | 3 test |
| 单元 (`test_html_assembler.py`) | 注入 `window.__hrTranslate` 和 `window.__hrContextIndex` 到 HTML | 2 test |
| 集成 (`test_html_assembler.py`) | `data-theme="dark"` 默认出现在 `<html>` 标签 | 1 test |
| 集成 (`test_html_assembler.py`) | Inter 字体 `<link>` 出现在 `<head>` (含 `display=swap`) | 1 test |
| 集成 (`test_html_assembler.py`) | Alpine.js `<script defer>` 出现在 `<head>` (URL 含 `alpinejs@3.13`) | 1 test |
| 集成 (`test_html_assembler.py`) | backdrop `<div>` 存在 + z-index 1000 在 `<aside>` style | 1 test |
| 回归 | 现有 visualization 测试 (含 18 个 Stage 1 data_loader test) 全绿 | 全绿 |
| 视觉 | 手动: 部署后浏览器打开, 检查 7 项 (见 §13) | 1 次手动 |

**测试维护原则**: 沿用 Stage 1 — 骨架断言, 不 snapshot 完整 HTML.

## 12. 影响范围

**只新增/修改**:

- 扩展: `src/tcfd_extractor/visualization/translations.py` (+~50 行, +30 词典条目)
- 修改: `src/tcfd_extractor/visualization/echarts.py` (~40 行变更, _t + 标题英文化 + 调色板)
- 重写: `src/tcfd_extractor/visualization/template.py` (~150 行 → ~250 行, 主题 + Alpine + 侧栏)
- 小改: `src/tcfd_extractor/visualization/html_assembler.py` (+~30 行, 注入 context 索引 + translator)
- 扩展: `tests/test_visualization/test_translations.py` (+5 test)
- 扩展: `tests/test_visualization/test_echarts.py` (+7 test)
- 扩展: `tests/test_visualization/test_html_assembler.py` (+4 test)

**净代码变化**: +约 280 行, **净增 ~280 行** (其中 ~40% 是测试, ~30% 是 template 主题 CSS)

**不动**: 主仓其它模块 / 数据流水线 / data_loader.py / 部署脚本 / 静态图 / Mermaid

## 13. 验证清单 (实施完成后)

- [ ] `grep -r "[\u4e00-\u9fff]" src/tcfd_extractor/visualization/echarts.py` 命中 ≤ 5 处 (仅 docstring 注释允许)
- [ ] `grep -r "[\u4e00-\u9fff]" src/tcfd_extractor/visualization/template.py` 命中 = 0 (template 100% 英文)
- [ ] `grep -c "data-theme=" output/report/index.html` 命中 1
- [ ] `grep -c "Inter:wght" output/report/index.html` 命中 1 (字体 link)
- [ ] `grep -c "alpinejs" output/report/index.html` 命中 1 (Alpine CDN)
- [ ] `grep -c "__hrTranslate" output/report/index.html` 命中 ≥ 5 (translator 注入)
- [ ] `grep -c "__hrContextIndex" output/report/index.html` 命中 = 1 (context 索引注入)
- [ ] `uv run pytest tests/test_visualization/` 全绿, 新增 ≥ 16 test
- [ ] `python scripts/build_report.py --output output/report/` 退出码 0
- [ ] `wc -c output/report/index.html` 介于 2.5MB-3.5MB (Stage 1 是 1.5-2MB, 增量为 context 索引 ~1MB)
- [ ] `python scripts/check_leakage.py output/report/index.html` 退出码 0
- [ ] 浏览器打开 `output/report/index.html`, 7 项客观检查:
  - (a) **暗色默认**: 首次访问页面背景近黑, 文字浅色
  - (b) **主题切换**: 点 header 角标 → 主题切换 + localStorage 写入 + 4 个 ECharts 图表自动重建适配新主题
  - (c) **Inter 字体**: 标题/KPI 数字视觉明显不同于 system-ui (更现代、字怀更紧)
  - (d) **全英文**: header / sections / 4 个 chart 标题/axis label 全部英文, 无中文 (除 `[[ZH: xxx]]` fallback 框)
  - (e) **Network 点击**: 点击任一节点 → 右侧滑出侧栏, 显示该关键词 1-3 条 context (中英对照), source + year 信息
  - (f) **Sankey 点击**: 点击任一连接边 → 侧栏显示 source → target 标题, 同样 context 列表
  - (g) **侧栏关闭**: ✕ 按钮 / ESC 键 / 点击图表区, 任一方式可关闭侧栏
- [ ] GitHub Pages 重新部署, `https://somAzzz.github.io/tcfd-report/` 200

## 14. Out of Scope

以下 4 项**不在本 spec 范围**, 留待后续:

- i18n 多语言切换 (中/英/日, 动态 locale)
- LLM 重新提取 snippet (而非复用 `context` 字段)
- Mermaid → ECharts 模块图迁移
- 服务端 SSR / 静态站点生成器
