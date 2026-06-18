# ECharts 可视化升级设计 (Stage 1) — Spec

**日期**: 2026-06-18
**作者**: 头脑风暴会话 (Stage 1 阶段)
**状态**: 待 spec 审阅

## 0. 背景与上下文

最近 (commit `5e6646e`) 已完成 HR 报告 GitHub Pages 部署 (`https://somAzzz.github.io/tcfd-report/`), 当前报告用 Plotly 渲染 3 个基础图 (donut / trend / bar)。 用户 (在 README.md:213 评论) 提议 8 项升级, 经头脑风暴确认拆为 2 个子项目:

- **Stage 1 (本 spec)**: 高级图表升级 (4 项): 关键词共现力导向网络 / 维度下钻旭日图 / 25 年河流图 / 流水线桑基图
- **Stage 2 (后续 spec)**: UI/UX 与交互升级 (4 项): 网格 + KPI / 语义色 / 字体 / Alpine.js + LLM tooltip

本次 spec 覆盖 Stage 1。 Stage 2 留待 Stage 1 完成后另起 spec。

**前置决策** (头脑风暴期间已锁):
1. 库选型: 全部 4 图用 **ECharts** (Plotly 退役)
2. 数据 scope 差异化: sunburst/streamgraph 25 年, force-directed 近 3 年, sankey 累计
3. 交互深度: 深度 (下钻/拖拽/缩放/路径高亮)
4. 落地方式: 路径 A (完全迁移, 删除 Plotly)

## 1. 目标

将 HR 报告的 3 个基础图表 (donut / trend / bar) 替换为 4 个 ECharts 高级交互图 (sunburst / streamgraph / force-directed / sankey), 保留 matplotlib 静态图 (refactor bar) 和 Mermaid 模块图, 单文件 HTML + CDN 部署模式不变。

**非目标** (避免范围蔓延):
- 不动 Stage 2 内容 (网格 / 主题色 / 字体 / Alpine.js / LLM tooltip)
- 不重跑任何数据流水线 (用现有 2023/2024/全量 JSONL + 聚类结果)
- 不改 GitHub Pages 部署流程 (沿用 Stage 0 验证过的 gh CLI + REST API)
- 不引入构建工具 (npm/webpack), 保持单文件 + ECharts CDN

## 2. 架构

```
                        输出数据源
  output/evaluate_cooccurrence/{2000..2024}/results.jsonl   ← 25 年 (sunburst/streamgraph)
  output/evaluate_cooccurrence/{2022,2023,2024}/            ← 近 3 年 (force-directed)
  output/tcfd_keywords/phase5_category_mapping/*_clusters.json  ← 3 维聚类 (sunburst)
  output/tcfd_keywords_summary.csv                          ← 1001 行公司×年 (sankey)
                          │
                          ▼
  data_loader.py [扩展, 4 个新方法]
    ├─ load_sunburst_data()      → {3 维 → 聚类 → 关键词} 树
    ├─ load_streamgraph_data()   → {year: {policy, market, tech}} 矩阵
    ├─ load_network_data()       → {nodes, links} 严格去重 + 动态 symbolSize
    └─ load_sankey_data()        → {nodes, links} 带 stage{N}_ 命名空间
                          │
                          ▼
  echarts.py [新建]
    ├─ TCFD_THEME_CONFIG         ← 主题色 + 字体 + 全局样式 (Stage 2 唯一改动点)
    ├─ _get_base_option()        ← 私有方法, 注入全局配置
    ├─ build_sunburst(data)      → (chart_id, option_dict)
    ├─ build_streamgraph(data)   → (chart_id, option_dict)
    ├─ build_network(data)       → (chart_id, option_dict)
    └─ build_sankey(data)        → (chart_id, option_dict)
                          │
                          ▼
  html_assembler.py [修改]  →  替换原 Plotly 调用, 4 个图 inline JSON 注入 HTML
                          │
                          ▼
  template.py [修改]  →  ECharts CDN (替代 Plotly CDN) + 渲染 try/catch 包装
                          │
                          ▼
  output/hr_report/index.html (单文件, 1.5-2MB, ECharts ~1MB + 4 图 inline JSON ~500KB + 模板 ~50KB)
```

**核心约束**: Python 端只生成 ECharts **option dict** (JSON 序列化), 不做渲染。 浏览器加载 ECharts CDN + 解析 inline JSON + 渲染交互图。

## 3. 文件结构 (改动一览)

| 文件 | 操作 | 责任 |
|---|---|---|
| `src/tcfd_extractor/visualization/echarts.py` | **新建** | TCFD_THEME_CONFIG + 4 个 builder + _get_base_option() |
| `src/tcfd_extractor/visualization/data_loader.py` | **扩展** | 新增 4 个聚合方法 |
| `src/tcfd_extractor/visualization/html_assembler.py` | **修改** | 替换 Plotly 调用为 echarts.py 调用, 4 图嵌入到对应 section |
| `src/tcfd_extractor/visualization/template.py` | **修改** | (a) 删 Plotly CDN, 改 ECharts CDN; (b) `<div class="plotly">` → `<div class="echarts" id="...">`; (c) 加 try/catch 渲染块 |
| `src/tcfd_extractor/visualization/chart_builders.py` | **删除** | Plotly 代码全部废弃, 后续 git history 可恢复 |
| `pyproject.toml` | **修改** | 移除 `plotly>=5.0.0` 依赖, 其它不变 |
| `tests/test_visualization/test_echarts.py` | **新建** | 4 个 builder 骨架断言测试 |
| `tests/test_visualization/test_data_loader.py` | **扩展** | 4 个新聚合方法单元测试 |
| `tests/test_visualization/test_html_assembler.py` | **扩展** | 1 个集成测试: 4 图 inline JSON 存在 |
| `scripts/build_hr_report.py` | **小改** | 输出大小预期从 3-4MB 调整为 1.5-2MB |

**新建 2 + 扩展 2 + 修改 2 + 删除 1 + 配置改 1** = 8 个文件改动。

## 4. TCFD_THEME_CONFIG 设计

`echarts.py` 顶部常量:

```python
TCFD_THEME_CONFIG = {
    "colors": {
        "policy": "#1f77b4",    # 政策蓝 (沉稳)
        "market": "#ff7f0e",    # 市场橙 (警示)
        "tech":   "#2ca02c",    # 技术绿 (霓虹)
        "neutral": ["#6c757d", "#adb5bd", "#dee2e6"],
    },
    "font": "Inter, 'Helvetica Neue', -apple-system, sans-serif",
    "text_style": {"fontFamily": "Inter", "color": "#222"},
    "tooltip_style": {
        "backgroundColor": "rgba(50,50,50,0.92)",
        "borderWidth": 0,
        "textStyle": {"color": "#fff", "fontSize": 12},
    },
    "global_roam": True,   # 全部图支持 zoom/pan (ECharts roam=true)
    "animation": True,
    "animation_duration": 800,
}
```

`_get_base_option(title, subtitle=None) -> dict`: 私有方法, 注入全局 textStyle/title/tooltip/grid, 返回 option dict 骨架。 4 个 builder 各自调一次, 复用公共部分。

**Stage 2 改动点**: 仅这一处, 加新色值 / 换字体 / 改 tooltip 样式。

## 5. 数据流详细 (4 个图)

### 5.1 Sunburst (25 年, 3 维)

| 维度 | 详情 |
|---|---|
| **数据源** | `output/tcfd_keywords/phase5_category_mapping/{政策,市场,技术}_clusters.json` |
| **数据 shape** | 树形: `[{name: '政策', children: [{name: '聚类1', children: [{name: '词', value: 12}, ...]}, ...]}]` |
| **聚合方法** | `load_sunburst_data() -> dict` |
| **ECharts series** | `series[0].type='sunburst'`, `data=[3 个根]`, `label.rotate='tangential'`, click 事件下钻 |
| **交互** | 点击内层节点 → 高亮路径 + 隐藏子树; 面包屑显示当前路径 |
| **空处理** | 某维度 `children` 为空 → 跳过该子树, log warning |

### 5.2 Streamgraph (25 年, 3 维)

| 维度 | 详情 |
|---|---|
| **数据源** | `output/evaluate_cooccurrence/<year>/summary.md` (已有 dim count) + 备用: 聚合 results.jsonl 的 dimension 字段 |
| **数据 shape** | `{"years": [2000, ..., 2024], "series": [{"name": "政策", "data": [12, 15, ...]}, ...]}` |
| **聚合方法** | `load_streamgraph_data() -> dict` |
| **ECharts series** | 3 个 `series`, 每个 `type='line'`, `stack='total'`, `areaStyle={opacity: 0.7}`, `smooth=True` |
| **交互** | ECharts `dataZoom=[{type: 'slider'}, {type: 'inside'}]` 支持时间区间缩放; legend 切换 dim |
| **空处理** | 某年某 dim 为 0 → 留空, 不报错 |

### 5.3 Force-directed (近 3 年: 2022-2024)

| 维度 | 详情 |
|---|---|
| **数据源** | `output/evaluate_cooccurrence/{2022,2023,2024}/results.jsonl` |
| **数据 shape** | `{"nodes": [{"id": "词A", "name": "词A", "symbolSize": 25, "category": 0, "value": 50}], "links": [{"source": "词A", "target": "词B", "weight": 12}], "categories": [{"name": "政策"}]}` |
| **聚合方法** | `load_network_data(years=[2022,2023,2024], top_n_edges=500, min_weight=5)` |
| **关键算法** | (1) 遍历 JSONL, 聚合 `(keyword_a, keyword_b) -> weight`; (2) 过滤 `weight >= min_weight`; (3) 排序取 top 500 边; (4) **遍历这 500 边, 维护 `seen: set[str]` 严格去重节点**; (5) **计算每个节点的 total_freq (出现次数), 映射 `symbolSize = 10 + total_freq * 0.5`** (范围 10-60); (6) 节点 category 按 `dimension` 字段 (政策/市场/技术/无) |
| **ECharts series** | `series[0].type='graph'`, `layout='force'`, `force.repulsion=80`, `draggable=True`, roam=True |
| **交互** | 节点可拖拽; hover 显示 label; 边粗细映射 weight; 类别 legend 切换 |
| **空处理** | 边数 < 50 → 自动降 `min_weight` 到 3 重试; 仍 < 50 → option 注入 `title.subtext` 提示 + `graphic` 中心提示 |
| **节点 ID** | 严格去重, 避免 ECharts 渲染失败 (重复 id 会导致 graph layout 异常) |

### 5.4 Sankey (累计)

| 维度 | 详情 |
|---|---|
| **数据源** | `output/tcfd_keywords_summary.csv` (1001 行公司×年) + 估算的 chunk/disclosure 总数 |
| **数据 shape** | `{"nodes": [{"name": "stage1_report_万科A_2023"}, {"name": "stage2_chunk_万科A_2023"}, ...], "links": [{"source": "stage1_report_万科A_2023", "target": "stage2_chunk_万科A_2023", "value": 152}, ...]}` |
| **聚合方法** | `load_sankey_data() -> dict` |
| **关键设计** | **所有节点加 `stage{N}_` 命名空间前缀**, 避免: (a) 公司名与阶段名碰撞, (b) 环状链路 (cyclic), (c) 节点混淆 |
| **命名空间规则** | `stage1_report_<id>_<year>` (原始报告) → `stage2_chunk_<id>_<year>` (文本分块) → `stage3_disclosure_<id>_<year>` (提取披露) → `stage4_dim_{policy/market/tech}` (维度归类) |
| **展示剥离** | ECharts `label.formatter = "params.name.replace(/^stage\\d+_/, '')"` 渲染时去掉前缀 |
| **节点聚合** | 阶段 4 维度归类合并所有公司 → 3 个聚合节点 (stage4_dim_policy 等), 避免单图节点爆炸 (>100 节点) |
| **ECharts series** | `series[0].type='sankey'`, `emphasis.focus='adjacency'`, `lineStyle.curve=0.5` |
| **交互** | hover 节点 → 高亮上下游路径 (`emphasis.focus='adjacency'`) |
| **空处理** | 阶段 2/3 估算数据缺失 → 用经验值 (报告 1 份 ≈ 150 分块 ≈ 15 披露) + log warning 标记估算来源 |

## 6. 关键决策

| 决策 | 选择 | 理由 |
|---|---|---|
| ECharts 主题 | 自定义 TCFD 主题 (3 维语义色 + Inter 字体) | 与 matplotlib 风格分开, 但统一在 TCFD_THEME_CONFIG |
| ECharts CDN | `https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js` | 与现有 Plotly CDN 模式一致, 5.5 稳定版 |
| 数据交付 | inline JSON (4 个 `<script>` 块) | 单文件约束; 浏览器 fetch 替代方案需破坏此约束 |
| HTML 大小 | 1.5-2MB (ECharts ~1MB + 4 图 inline JSON ~500KB + 模板 ~50KB) | 单文件 GitHub Pages 限制 100MB, 充裕 |
| Plotly 移除 | 立即移除 (删除 `chart_builders.py` + 依赖) | 用户选 A 完全迁移; 留兜底会双倍体积且风格割裂 |
| Force-directed 边数 | Top 500 边 (默认), `min_weight=5` 起步, 自动降阈值到 3 | 3 年 ~10K 边 → 500 边视觉清晰; 极端稀疏自动重试 |
| Force-directed symbolSize | `10 + total_freq * 0.5` (范围 10-60) | 高频核心词自动放大, 避免千词一面 |
| Sankey 命名空间 | 所有节点加 `stage{N}_` 前缀, formatter 剥离 | 避免环状/碰撞/混淆 (你的 §3 反馈) |
| Sunburst 钻取 | 点击内层 → 高亮路径, 面包屑显示 | ECharts 原生支持 |
| 浏览器端 try/catch | `try { setOption } catch { 灰底 + 失败提示 }` | 单图失败不阻断全页 (你的 §5 反馈) |
| Worktree | 不使用, 沿用 main | 与上次部署决策一致, 任务独立可逆 |
| 测试策略 | 骨架断言 (不 snapshot 完整 dict) | Stage 2 改样式不破坏测试 (你的 §6 反馈) |
| Stage 1 文档 | 新建 1 spec (本文件) + 1 plan + 1 subagent-driven 实施 | 沿用上次的 spec → plan → execution 流程 |

## 7. 错误处理

| 失败点 | 检测 | 处理 |
|---|---|---|
| 数据源文件缺失 | `Path.exists()` 检查 | 抛 `DataSourceNotFound` (在 `data_loader` 抛, build 中止) |
| Cluster JSON 格式错误 | JSON parse + 必填字段校验 | 抛 `DataFormatError`, log 哪个文件哪行 |
| Sunburst 节点为 0 | 树深度检查 | 跳过该维度的子树, log warning, 渲染空分类 |
| Streamgraph 全 0 | 矩阵检查 | 渲染空图 + 提示 "无数据" |
| Force-directed 边数 < 50 | 计数检查 | 自动降 `min_weight` 到 3 重试一次, 仍 < 50 → option 注入 `title.subtext` 提示 + `graphic` 中心文字 |
| Force-directed 节点重复 id | 集合去重 (`seen: set[str]`) | 重复跳过, log warning; 不会渲染失败 |
| Sankey 节点重复名 | 命名空间前缀 (`stage{N}_`) | 不会发生, 设计层面杜绝 |
| Sankey 形成环 | link DAG 检查 | 若发现环, 抛 `CyclicLinkError` 中止该图构建 |
| ECharts 浏览器端渲染失败 | `try { chart.setOption } catch (e)` | div 背景设 `#f0f0f0`, 居中显示 "图表渲染失败, 请检查数据格式", `console.error` 留 log |
| `check_leakage.py` 失败 | exit code | 沿用现有逻辑, abort build |
| HTML 大小超过 5MB | 累加 4 图 JSON + ECharts CDN + 模板大小 | 超过则抛 `HTMLSizeExceeded` 警告 + 让用户决策 |
| pyproject.toml plotly 仍在 import | 静态检查 + 导入测试 | `grep -r "import plotly" src/` 失败, ci 卡住 |

## 8. 测试

| 测试类型 | 覆盖 | 数量目标 |
|---|---|---|
| 单元 (data_loader) | 4 个新聚合方法: 正常数据 + 边界 (空/单条/超大) | 4 方法 × 3 case = 12 test |
| 单元 (echarts builders) | 4 个 builder 输出 option dict **骨架**断言 (type, data 长度, 关键字段) | 4 builders × 2 case = 8 test |
| 单元 (TCFD_THEME_CONFIG) | 主题色 hex 格式校验, 字体字段非空, roam=True | 1 test |
| 集成 (html_assembler) | 全 build 跑通, 4 个图 inline `<script>` 块存在, ECharts CDN 引用 | 1-2 test |
| 集成 (ECharts 配置静态校验) | 4 个 option dict 通过 ECharts `setOption` schema 校验 (用 ECharts 官方 schema 或自写) | 1 test |
| 回归 | 现有 65 个 visualization 测试不挂 | 全绿 |
| 视觉 | 手动: 部署后浏览器打开, 检查 4 图可渲染 + 交互正常 | 1 次手动 |

**测试维护原则** (你的 §6 反馈): snapshot 测试只断言**核心骨架** (type, data 长度, 关键字段), 不 snapshot 完整 dict, 避免 Stage 2 调样式时大面积失效。

## 9. 影响范围

**只新增/修改**:

- 新增: `src/tcfd_extractor/visualization/echarts.py` (~300 行)
- 新增: `tests/test_visualization/test_echarts.py` (~200 行)
- 扩展: `src/tcfd_extractor/visualization/data_loader.py` (+4 方法, ~150 行)
- 扩展: `tests/test_visualization/test_data_loader.py` (+12 test, ~150 行)
- 修改: `src/tcfd_extractor/visualization/html_assembler.py` (~30 行变更)
- 修改: `src/tcfd_extractor/visualization/template.py` (~20 行变更)
- 删除: `src/tcfd_extractor/visualization/chart_builders.py` (~150 行)
- 修改: `pyproject.toml` (移除 plotly 依赖)
- 修改: `scripts/build_hr_report.py` (输出大小预期文案)
- 修改: `README.md` (HR 报告章节加 "ECharts 4 个高级图" 说明)

**净代码变化**: +约 800 行, -约 150 行, **净增 ~650 行** (其中 ~50% 是测试)

**不动**: 主仓其它模块 / 数据流水线 / GitHub 部署流程 / 静态图 (refactor bar) / Mermaid 模块图

## 10. 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| ECharts 5.5 API 在边缘 case 行为变化 | 4 图渲染异常 | 用稳定 5.5.0 (锁版本), 1 个 schema 静态校验 test |
| 单文件 1.5-2MB 加载慢 (网络) | 用户体验下降 | ECharts CDN 走 jsdelivr (国内可访问); 浏览器缓存 ECharts |
| 移除 Plotly 后, 现有 65 个 visualization 测试中有依赖 | 回归失败 | grep `from tcfd_extractor.visualization.chart_builders` 找引用, 全部改为 echarts.py; CI 卡住 |
| Sankey 阶段 2/3 估算数据不准确 | 数字失真 | log warning 标记 "估算", 后续可接入真实 chunk/disclosure 计数 |
| Force-directed 边数 500 不足以体现核心节点 | 信息密度低 | 备选: 边数做成 slider, 用户从 100 调到 2000 |

## 11. 后续 (Stage 2, 不在本 spec 范围)

- 网格 + KPI 卡片布局 (替换瀑布流)
- 语义色 + 暗色模式 (基于现有 TCFD_THEME_CONFIG 扩展)
- Inter 字体 + 留白优化
- Alpine.js 状态管理 + LLM-extracted snippet tooltip (需 LLM 重新跑提取)
- 模块图从 Mermaid 迁到 ECharts (可选, 暂不决策)

## 12. 验证清单 (实施完成后)

- [ ] `grep -r "import plotly" src/` 返回空
- [ ] `grep -r "from tcfd_extractor.visualization.chart_builders" src/ tests/ scripts/` 返回空
- [ ] `uv run pytest tests/test_visualization/` 全绿, 新增 ≥ 20 test
- [ ] `python scripts/build_hr_report.py --output output/hr_report/` 退出码 0
- [ ] `wc -c output/hr_report/index.html` 介于 1.5MB-2.0MB
- [ ] `grep -c 'echarts.init' output/hr_report/index.html` 命中 4
- [ ] `python scripts/check_leakage.py output/hr_report/index.html` 退出码 0
- [ ] 浏览器打开, 4 图渲染成功 + 交互正常 (sunburst 点击下钻, network 拖拽节点, streamgraph 缩放, sankey hover 高亮)
- [ ] GitHub Pages 重新部署, `https://somAzzz.github.io/tcfd-report/` 200
