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
  output/hr_report/index.html (单文件, ~1.5-2MB)
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
| `scripts/build_hr_report.py` | **不改** | 沿用 |

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
"无": "None",

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
"维度归类": "Dimension Classification",
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

### 5.3 翻译注入点

| 位置 | 翻译内容 | 实现方式 |
|---|---|---|
| `echarts.py` 各 builder | chart title / subtitle / axis label / legend | 直接硬编码英文 (避免运行时查表性能开销) |
| `echarts.py` tooltip formatter | 节点名 / 维度名 / 频次 | `formatter: "function(p) { return window.__hrTranslate(p.name) + ' (' + p.value + ' occurrences)'; }"` |
| `echarts.py` sankey label formatter | 节点名剥离 stage{N}_ 前缀 | 沿用 Stage 1, 但加 `_t()` 翻译后置 |
| `template.py` 静态文本 | header / sections / captions / Mermaid | 直接写英文 |
| `template.py` 侧栏模板 | 标题 / 维度徽章 | Alpine 模板表达式 `x-text="panel.dimension ? window.__hrTranslate(panel.dimension) : ''"` |
| `html_assembler.py` 注入 | 节点 → context 列表索引 | JSON 注入到 `<script>`, context 文本也走 `translate_smart()` (中英对照) |

## 6. ECharts 暗色主题适配

### 6.1 动态主题切换

每个 `chart.setOption(opt)` 之前, 读取 CSS 变量, 动态调整 option:

```javascript
function applyTheme(opt) {
  const theme = document.documentElement.dataset.theme;
  const isDark = theme === 'dark';
  const fg = isDark ? '#e6e6e6' : '#222';
  const muted = isDark ? '#8b95a1' : '#666';
  const cardBg = isDark ? '#1a1f24' : '#ffffff';

  // 全局 textStyle
  opt.textStyle = { ...opt.textStyle, color: fg };

  // 标题
  if (opt.title) opt.title.textStyle = { ...opt.title.textStyle, color: fg };

  // X/Y 轴
  ['xAxis', 'yAxis'].forEach(k => {
    if (opt[k]) {
      opt[k].axisLine = { lineStyle: { color: muted } };
      opt[k].axisLabel = { color: muted };
      opt[k].splitLine = { lineStyle: { color: muted, opacity: 0.2 } };
    }
  });

  // Legend
  if (opt.legend) opt.legend.textStyle = { color: fg };

  return opt;
}

// 4 个图都包装
echarts.init(document.getElementById('echarts-sunburst')).setOption(applyTheme({{ sunburst_json|safe }}));
```

**简化方案**: ECharts 支持 `chart.dispose()` + 重新 init。 切主题时销毁旧实例, 用新 option 重建。 重建比 patch 简单且稳定, 牺牲一点切换动画 (200ms 内完成).

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

### 7.1 全局 state (body 根)

```html
<body x-data="{
  theme: localStorage.getItem('hr-theme') || 'dark',
  panel: null,
  toggleTheme() {
    this.theme = this.theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('hr-theme', this.theme);
    document.documentElement.dataset.theme = this.theme;
    rebuildAllCharts();  // 重新 4 个图实例, 应用新主题
  },
  openPanel(data) { this.panel = data; },
  closePanel() { this.panel = null; }
}"
x-init="document.documentElement.dataset.theme = theme">
```

### 7.2 ECharts → Alpine 联动 (click)

```javascript
// Network chart
networkChart.on('click', params => {
  if (params.dataType === 'node') {
    const keyword = params.data.name;
    const contexts = (window.__hrContextIndex.keywords[keyword] || []).slice(0, 3);
    Alpine.store('hrApp').openPanel({
      type: 'node',
      title: window.__hrTranslate(keyword),
      dimension: params.data.category,
      contexts: contexts
    });
  }
});

// Sankey chart
sankeyChart.on('click', params => {
  if (params.dataType === 'edge') {
    const source = params.data.source;
    const target = params.data.target;
    const contexts = (window.__hrContextIndex.sankey[`${source}->${target}`] || []).slice(0, 3);
    Alpine.store('hrApp').openPanel({
      type: 'link',
      title: `${window.__hrTranslate(source)} → ${window.__hrTranslate(target)}`,
      contexts: contexts
    });
  }
});
```

**Hover 仍由 ECharts 原生 tooltip 处理** (不经过 Alpine), 避免 DOM 抖动掉帧 (你的 §2.1 反馈).

### 7.3 侧栏 UI

```html
<aside x-show="panel" x-transition.opacity.duration.250ms
       @keydown.escape.window="closePanel()"
       class="hr-side-panel"
       :class="{ 'hr-side-panel--open': panel }">
  <header>
    <h3 x-text="panel ? panel.title : ''"></h3>
    <span class="dim-badge" x-text="panel && panel.dimension ? panel.dimension : ''"></span>
    <button @click="closePanel()">✕</button>
  </header>
  <div class="hr-side-panel__body">
    <template x-if="panel && panel.contexts.length === 0">
      <p class="muted">No context samples available for this item.</p>
    </template>
    <template x-for="ctx in panel ? panel.contexts : []" :key="ctx.id">
      <article class="context-card">
        <p class="context-zh" x-text="ctx.original"></p>
        <p class="context-en" x-text="ctx.translated"></p>
        <footer>
          <span x-text="ctx.source"></span>
          <span x-text="ctx.year"></span>
        </footer>
      </article>
    </template>
  </div>
</aside>
```

CSS: 固定 right: 0, top: 0, width: 420px, height: 100vh, transform: translateX(100%) → translateX(0) 滑入.

## 8. context 索引注入 (`html_assembler.py`)

为支持点击侧栏, 需在 HTML 中注入节点→context 的反向索引:

```python
def build_context_index(eval_dir, years):
    """Build keyword → [context, ...] index for tooltip side panel."""
    index = {"keywords": {}, "sankey": {}}
    for year in years:
        jsonl = eval_dir / str(year) / "results.jsonl"
        if not jsonl.exists():
            continue
        with jsonl.open(encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                if not r.get("is_tcfd_related"):
                    continue
                ctx = r.get("context", "").strip()
                if not ctx:
                    continue
                # 关键词索引
                for kw in (r.get("keyword_a", ""), r.get("keyword_b", "")):
                    if kw:
                        index["keywords"].setdefault(kw, []).append({
                            "id": f"{year}-{r.get('file','')}-{len(index['keywords'].get(kw, []))}",
                            "original": ctx,
                            "translated": translate_smart(ctx),
                            "source": r.get("file", "").split("/")[-1],
                            "year": year,
                            "dimension": r.get("dimension", ""),
                        })
    # 限制每个关键词最多 3 条 (避免注入过大)
    for kw in index["keywords"]:
        index["keywords"][kw] = index["keywords"][kw][:3]
    return index
```

**注入方式**: `<script>window.__hrContextIndex = {...};</script>` 放在 `<head>` ECharts CDN 之后, Alpine 初始化之前.

**体积估算**: ~3 年 × ~5000 行 × 平均 2 关键词 × 平均 50 char × 3 sample ≈ 4.5MB 文本 → **限制每个关键词 3 条 sample** 后降到 ~1.5MB. 可接受.

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
| 单元 (`test_echarts.py`) | `_t()` helper: 命中词典 / 纯 ASCII / `[[ZH: xxx]]` 包裹 | 3 test |
| 单元 (`test_html_assembler.py`) | 注入 `window.__hrTranslate` 和 `window.__hrContextIndex` 到 HTML | 2 test |
| 集成 (`test_html_assembler.py`) | `data-theme="dark"` 默认出现在 `<html>` 标签 | 1 test |
| 集成 (`test_html_assembler.py`) | Inter 字体 `<link>` 出现在 `<head>` | 1 test |
| 集成 (`test_html_assembler.py`) | Alpine.js `<script defer>` 出现在 `<head>` | 1 test |
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
- [ ] `grep -c "data-theme=" output/hr_report/index.html` 命中 1
- [ ] `grep -c "Inter:wght" output/hr_report/index.html` 命中 1 (字体 link)
- [ ] `grep -c "alpinejs" output/hr_report/index.html` 命中 1 (Alpine CDN)
- [ ] `grep -c "__hrTranslate" output/hr_report/index.html` 命中 ≥ 5 (translator 注入)
- [ ] `grep -c "__hrContextIndex" output/hr_report/index.html` 命中 = 1 (context 索引注入)
- [ ] `uv run pytest tests/test_visualization/` 全绿, 新增 ≥ 16 test
- [ ] `python scripts/build_hr_report.py --output output/hr_report/` 退出码 0
- [ ] `wc -c output/hr_report/index.html` 介于 2.5MB-3.5MB (Stage 1 是 1.5-2MB, 增量为 context 索引 ~1MB)
- [ ] `python scripts/check_leakage.py output/hr_report/index.html` 退出码 0
- [ ] 浏览器打开 `output/hr_report/index.html`, 7 项客观检查:
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
