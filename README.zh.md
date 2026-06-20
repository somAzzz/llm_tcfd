# TCFD 关键词提取系统

> A Chinese-language NLP system for extracting **TCFD** (Task Force on Climate-related Financial Disclosures) keywords from annual reports of A-share listed companies in China, with subsequent co-occurrence analysis, semantic validation, K-Means clustering, and LLM-based TCFD relevance evaluation.

[English version](./README.md)

---

## 目录

- [项目简介](#项目简介)
- [核心特性](#核心特性)
- [快速开始](#快速开始)
- [架构](#架构)
- [模块说明](#模块说明)
- [HR 可视化报告](#hr-可视化报告)
- [Output 目录关系图](#output-目录关系图)
- [数据假设](#数据假设)
- [测试](#测试)
- [开发与重构记录](#开发与重构记录)
- [贡献](#贡献)
- [许可证](#许可证)

---

## 项目简介

本项目是一个面向中国 A 股上市公司年报的 **TCFD（气候相关财务披露）关键词提取与分析系统**。它从年报正文中识别气候相关披露内容,沿"政策（Policy）"、"市场（Market）"、"技术（Technology）"三个维度对提取的关键词进行分类与评估。

完整流水线包括:

1. **年报采样与分块** —— 采样年报,按段落/句子边界切分为语义块
2. **关键词提取** —— 基于本地 LLM（SGLang, Qwen3.5-35B-A3B）抽取 TCFD 关键词
3. **共现分析** —— 在窗口或句子范围内统计关键词共现关系
4. **语义聚类** —— K-Means 聚类 + sentence-transformers 语义验证
5. **TCFD 评估** —— LLM 评估共现片段的 TCFD 相关性,生成维度分布总结

## 核心特性

- **多维度分类**:政策 / 市场 / 技术三个 TCFD 维度
- **本地 LLM 推理**:通过 OpenAI 兼容协议调用本地 SGLang 服务
- **并发批处理**:ThreadPoolExecutor + tqdm,支持重试与中断
- **流式内存安全**:生成器流式加载,避免一次性加载所有数据
- **集中化配置**:基于 pydantic-settings v2,支持环境变量覆盖
- **结构化异常**:自定义异常层次,支持细粒度错误处理
- **零 subprocess 依赖**:批处理纯函数化,便于测试与集成

## 快速开始

### 环境要求

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) (推荐包管理工具)
- 本地 SGLang 服务(或其他 OpenAI 兼容 LLM 端点)

### 安装

```bash
# 克隆仓库
git clone <repo-url>
cd frequency_analyzer

# 同步依赖
uv sync            # 仅运行时依赖
uv sync --dev      # 包含 dev 依赖(推荐)
```

### 配置

通过环境变量自定义（可选,均有默认值）:

```bash
export TCFD_LLM_BASE_URL="http://127.0.0.1:30000/v1"
export TCFD_LLM_MODEL_NAME="Qwen/Qwen3.5-35B-A3B"
export TCFD_LLM_API_KEY="sk-local"
export TCFD_LLM_TIMEOUT=60
export TCFD_LLM_TEMPERATURE=0.1

export TCFD_PATH_INPUT_ROOT="output/frequency/cooccurrence_context"
export TCFD_PATH_OUTPUT_ROOT="output/evaluate_cooccurrence"

export TCFD_BATCH_WORKERS=8
export TCFD_BATCH_MAX_RETRIES=3
export TCFD_BATCH_RETRY_DELAY=1.0
```

### 运行

```bash
# 完整流水线
python -m tcfd_extractor.main

# 词袋校验 CLI
python -m tcfd_extractor --input <file> --output <file>

# 频率分析
python -m tcfd_extractor.frequency.main [options]

# 关键词聚类
python -m tcfd_extractor.clustering.main --input <dir> --output <dir>

# TCFD 评估(单目录)
python -m tcfd_extractor.evaluation.evaluate_cooccurrence \
    --input-dir output/frequency/cooccurrence_context/2020 \
    --output output/evaluate_cooccurrence/2020/results.jsonl \
    --summary output/evaluate_cooccurrence/2020/summary.md

# TCFD 评估(按年份批量)
python -m tcfd_extractor.evaluation.batch_evaluate_cooccurrence \
    --year 2020
```

## 架构

```
src/tcfd_extractor/
├── main.py                              # 主入口:采样 → 提取 → 频率统计
├── sampler.py                           # 年报采样
├── chunker.py                           # 文本分块(尊重段落/句子边界)
├── extractor.py                         # LLM 关键词提取(OpenAI API)
├── executor.py                          # 线程池并发执行器
├── evaluator.py                         # (旧)评估器入口
├── aggregator.py                        # 结果聚合 / 导出
├── tcfd_word_bag_validator.py           # 词袋校验 CLI
├── config.py                            # 全局配置(LLM/Path/Batch Pydantic Settings)
├── evaluation/                          # 评估模块(2026-06 重构)
│   ├── models.py                        # Pydantic 数据模型
│   ├── parser.py                        # Markdown 共现上下文解析
│   ├── prompts.py                       # LLM 提示词常量
│   ├── evaluator.py                     # 单条 LLM 评估器
│   ├── batch.py                         # 批量评估(并发 + 流式)
│   ├── summary.py                       # 统计计算 + 总结生成
│   ├── exceptions.py                    # 自定义异常层次
│   ├── cooccurrence_evaluator.py        # 薄壳 re-export(向后兼容入口)
│   ├── evaluate_cooccurrence.py         # 单目录评估 CLI
│   └── batch_evaluate_cooccurrence.py   # 按年份批量评估 CLI
├── frequency/                           # 词频统计
│   ├── counter.py                       # 关键词计数(归一化到每万字)
│   ├── parser.py                        # 年报文件名解析
│   └── cooccurrence.py                  # 共现分析(固定窗口 / 句子模式)
├── clustering/                          # 关键词聚类
│   ├── clustering.py                    # K-Means + silhouette K 选择
│   ├── validator.py                     # sentence-transformers 语义验证
│   ├── label_generator.py               # 可选 LLM 聚类标签生成
│   └── exporter.py                      # 导出 + t-SNE 可视化
└── visualization/                       # HR 报告生成(2026-06 新增)
    ├── anonymize.py                     # 单向 SHA-256 公司名脱敏
    ├── translations.py                  # 中→英关键词映射(~140 条)
    ├── data_loader.py                   # 25 年 JSONL 加载 + 聚合
    ├── echarts.py                       # ECharts option 构建 + JS formatter 编码
    ├── pipeline_metrics.py              # 工程健康指标定义
    ├── static_charts.py                 # 兼容保留的静态 SVG helper
    ├── module_graph.py                  # AST 自动发现模块依赖
    ├── html_assembler.py                # 数据包契约 + HTML 组装边界
    └── template.py                      # Jinja2 HTML 模板
```

## 模块说明

### 1. 关键词提取(`tcfd_extractor`)

- `main.py` —— 主流程编排
- `sampler.py` —— 从年报库中按公司/年份采样
- `chunker.py` —— 长文本切分为语义块
- `extractor.py` —— 调用 LLM 抽取 TCFD 关键词
- `executor.py` —— 线程池执行 + 信号量限流
- `aggregator.py` —— 合并去重,导出 JSON / CSV

### 2. 频率统计(`tcfd_extractor.frequency`)

- `counter.py` —— 关键词计数,按每万字归一化
- `cooccurrence.py` —— 共现分析,支持固定窗口与句子两种模式
- `parser.py` —— 解析 `{company_id}-{company_name}-{year}年年度报告.txt` 文件名

### 3. 聚类(`tcfd_extractor.clustering`)

- `clustering.py` —— K-Means 聚类,自动选择最优 K(silhouette 分数)
- `validator.py` —— 使用 sentence-transformers 做语义验证
- `exporter.py` —— 导出聚类结果与 t-SNE 可视化

### 4. 评估(`tcfd_extractor.evaluation`)

由 2026-06 重构拆出,原 468 行上帝类已拆为 8 个聚焦模块(详见"开发与重构记录")。

- `models.py` —— 数据模型:`CooccurrenceContext` / `TCFDValidationResult` / `EvaluationResult` / `FileParseResult`
- `parser.py` —— 共现上下文 MD 文件解析(含路径 fallback)
- `prompts.py` —— LLM 提示词常量(评估 / 总结)
- `evaluator.py` —— `CooccurrenceEvaluator`:单条 LLM 评估,带异常捕获与原始响应日志
- `batch.py` —— `BatchEvaluator`:并发 + 流式批处理,失败终止
- `summary.py` —— `compute_statistics` + `generate_summary`
- `exceptions.py` —— `EvaluationError` / `LLMEvaluationError` / `LLMUnavailableError` / `LLMResponseParseError` / `LLMTimeoutError`
- `cooccurrence_evaluator.py` —— 薄壳 re-export(向后兼容,新代码应直接 import 子模块)

### 5. 报告生成(`tcfd_extractor.visualization`)

将 25 年评估结果聚合成一个**自包含的交互式 HTML 报告**,可直接用于 GitHub Pages 部署:

- `anonymize.py` —— 单向 SHA-256 公司名脱敏(`Company #001` 风格,无反向表)
- `translations.py` —— 中→英关键词映射表(~140 条),UI 全英文,数据保留中文
- `data_loader.py` —— JSONL 批量加载 + KPI/维度/年份/Top 共现词对聚合
- `echarts.py` —— Sunburst / Streamgraph / Network / Sankey / 工程图表的 ECharts option 构建
- `pipeline_metrics.py` —— 注入报告数据包的工程健康指标
- `static_charts.py` —— 为兼容保留的静态 SVG helper
- `module_graph.py` —— AST 解析本地模块 import 关系
- `html_assembler.py` —— 构建 `ReportDataBundle` 数据契约,再渲染 Jinja2
- `template.py` —— Jinja2 内联 HTML 模板(5 区块 + 隐藏 Tech Deep Dive)

### 6. 工具与脚本(`scripts/`)

- `tcfd_word_bag_validator.py` —— 词袋校验 CLI
- `build_report.py` —— 报告生成编排器(数据 → HTML + 泄漏检查)
- `check_leakage.py` —— Pre-push 泄漏检查(公司名 + 邮箱 + 电话 + TODO 等模式)

## 可视化报告

**🌐 在线演示**: https://somAzzz.github.io/tcfd-report/

`visualization` 包内置一个完整的"研究项目 → 作品集 HTML"流水线,可用于对外展示项目成果(如求职时向 HR / 面试官展示)。

### 一键生成

### 高级图表 (ECharts, Stage 1)

- **Sunburst** — 3 维 (政策/市场/技术) 聚类层级下钻
- **Streamgraph** — 2000-2024 年 3 维披露演变, 可拖动时间缩放
- **Force-directed Network** — 近 3 年 (2022-2024) 关键词共现, 节点可拖拽
- **Sankey** — NLP 流水线数据提纯 (10,814 报告 → 维度归类)

底层用 ECharts 5.5 CDN, 单文件 HTML 仍可 (1.5-2MB)。

```bash
# 生成报告(默认 GitHub Pages 模式,CDN 加载 JS,~1.5 MB)
python scripts/build_report.py --output output/report/

# 邮箱附件模式(JS 内联,无需网络,~4 MB)
python scripts/build_report.py --output output/report/email/ --inline
```

### 输出结构

```
output/report/
├── index.html      # 自包含的交互式报告(打开即用)
├── README.md       # 部署说明
└── .nojekyll       # GitHub Pages 配置
```

### 报告内容(5 区块)

1. **What is this project about?** —— 动态 KPI 卡片 + TCFD 维度/聚类 Sunburst
2. **What We Built** —— 6 阶段流水线 Mermaid + "Beyond TCFD: Reusable Architecture" 展示卡
3. **What We Discovered** —— 年度 Streamgraph + 近三年共现网络 + 流水线 Sankey
4. **Robust AI Pipeline Engineering** —— 工程健康 ECharts dashboard
5. **Tech Deep Dive** —— 点击展开的模块依赖图(AST 自动发现)

### 设计原则

- **双层受众**:非技术 HR(30 秒看懂 KPI) + 技术 HR(展开 Tech Deep Dive 看架构)
- **数据隐私**:公司名单向 SHA-256 哈希(无反向表),`output/report/` 不进 git
- **部署友好**:单文件 HTML,可直接 GitHub Pages 部署
- **泄漏安全**:推送到公开仓库前必须通过 `scripts/check_leakage.py`

### GitHub Pages 部署

1. 创建新公开仓库 `tcfd-report`(与主项目隔离)
2. 推送 `index.html` + `README.md` + `.nojekyll`
3. Settings → Pages → Branch: `main` → Save
4. 获得 `https://somAzzz.github.io/tcfd-report/` 公开链接

## Output 目录关系图

`output/` 下的生成数据被主仓库忽略,其中混有正式流水线产物、私有实验产物和
独立的公开报告发布仓库。当前关系图、公开安全说明和可归档候选见
[OUTPUT.md](./OUTPUT.md)。

## 数据假设

- **年报数据**:`/home/bo/projects/data/A股年报/` 按年份子目录组织
- **文件名格式**:`{company_id}-{company_name}-{year}年年度报告.txt`(也支持下划线)
- **文件类型**:纯文本(`.txt`)
- **共现输出**:Markdown(`.md`),由 `tcfd_extractor.frequency` 生成

## 测试

```bash
# 全量测试
uv run pytest

# 指定测试文件
uv run pytest tests/test_config.py

# 测试目录
uv run pytest tests/test_frequency/

# 带覆盖率
uv run pytest --cov=src/tcfd_extractor
```

测试组织:

- `tests/test_config.py` —— 全局配置 + 线程安全(18 + 3 测试)
- `tests/test_cooccurrence_evaluator.py` —— 向后兼容(16 测试)
- `tests/evaluation/` —— 评估模块单元测试 + 集成测试
  - `test_exceptions.py` —— 异常层次(7)
  - `test_models.py` —— 数据模型(12)
  - `test_prompts.py` —— 提示词常量(9)
  - `test_parser.py` —— Markdown 解析(10)
  - `test_evaluator.py` —— 单条 LLM 评估(7)
  - `test_batch.py` —— 批量评估(8)
  - `test_summary.py` —— 统计 + 总结(8)
  - `test_integration.py` —— 端到端集成测试(3)
- `tests/test_visualization/` —— 可视化报告测试
  - `test_anonymize.py` —— 脱敏(14)
  - `test_translations.py` —— 中→英映射 + 覆盖率(12)
  - `test_data_loader.py` —— JSONL 加载 + 聚合(14)
  - `test_static_charts.py` —— matplotlib + SVG(5)
  - `test_module_graph.py` —— AST 依赖发现(5)
  - `test_html_assembler.py` —— 端到端模板渲染(7,部分需 PYTHONPATH=src)
- `tests/test_frequency/` —— 频率统计测试
- `tests/test_clustering/` —— 聚类测试

**全量统计**:228 测试通过(2 个预存在损坏文件 + 1 个预存在 collection 错误已忽略)

## 开发与重构记录

### 2026-06: 评估模块重构

**目标**:拆分 `src/tcfd_extractor/evaluation/cooccurrence_evaluator.py` 的 468 行上帝类,建立全局 config,消除 subprocess,扩展测试覆盖。

**变更摘要**:

| 项目 | 数值 |
|---|---|
| 上帝类行数 | 468 → 79(83% 缩减) |
| 新增模块 | 8 个(evaluator/batch/summary/parser/prompts/models/exceptions/config) |
| 新增测试 | 95+ |
| 全量测试 | 165 passed(目标 101) |
| 新模块覆盖率 | 95-100% |
| subprocess 调用 | 0 |
| `print()` 使用 | 0 |

**主要 DoD 验收点**:

- ✅ 全量测试通过(165 passed)
- ✅ 新模块覆盖率 ≥ 90%
- ✅ 无 subprocess 调用
- ✅ 无 `print()` 使用
- ✅ 薄壳行数 ≤ 80(目标 50-60,实际 79 含向后兼容包装)
- ✅ 畸形 JSON 防御(`LLMResponseParseError` + 原始响应日志)
- ✅ 配置线程安全(concurrent reads)
- ✅ 现有 16 个向后兼容测试零修改通过(注:经用户批准进行了必要的 baseline 修正与 mock 路径迁移)

### 2026-06: 可视化报告模块(作品集 HTML 生成)

**目标**:新增 `tcfd_extractor.visualization` 包,将 25 年评估结果聚合成一个**自包含的交互式 HTML 报告**,可作为对外展示项目成果的作品集(尤其适合求职场景下向 HR / 面试官展示工程能力)。

**变更摘要**:

| 项目 | 数值 |
|---|---|
| 新增模块 | 8 个(`anonymize` / `translations` / `data_loader` / `static_charts` / `module_graph` / `html_assembler` / `template`) |
| 新增脚本 | 2 个(`build_report.py` 编排器,`check_leakage.py` 预推送泄漏检查) |
| 新增测试 | 65(7 个测试文件) |
| 全量测试 | 228 passed(目标 ≥ 200) |
| HTML 报告大小 | 121 KB(CDN 模式) |
| subprocess 调用 | 0 |
| `print()` 使用 | 0 |

**主要 DoD 验收点**:

- ✅ `output/report/index.html` 可双击打开(无服务器)
- ✅ Above-the-fold 含 "annual report" + "climate/tcfd/keyword"
- ✅ 5 个区块全部渲染(Hero / What We Built / What We Discovered / Engineering / Tech Deep Dive)
- ✅ 中→英双语 tooltip(关键词原文 + 英文翻译)
- ✅ 营销文案"Reusable Architecture"通过外部 review(spec §6)
- ✅ Leakage check 通过(无真实公司名 / 邮箱 / 电话 / TODO 残留)
- ✅ Anonymization 真正单向(SHA-256,1000 buckets,无反向表)
- ✅ 模块依赖图通过 AST 自动发现(无手维护)
- ✅ `git diff tests/test_cooccurrence_evaluator.py` 为空(向后兼容)

**GitHub Pages 部署**(推荐):将 `output/report/` 推送到独立的 `tcfd-report` 公开仓库,获得 `https://somAzzz.github.io/tcfd-report/` 链接,可直接放入求职邮件正文。

## 贡献

欢迎提交 issue 和 PR。提交前请确保:

- 所有测试通过
- 新增功能附带测试
- 遵循已有代码风格
- 重要变更更新本 README

## 许可证

本项目仅供研究使用。
