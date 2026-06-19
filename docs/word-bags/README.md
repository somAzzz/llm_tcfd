# 词袋目录说明

本目录按**处理阶段**组织 TCFD 词袋的不同版本，方便追踪词袋演变与各模块引用。

## 目录结构

```
doc/word-bags/
├── raw/                # 原始未处理词袋（来源数据）
│   ├── 词袋A.md
│   ├── 词袋A.json
│   └── words_bag.md    # 旧版词袋（policy/market/tech 维度格式）
├── merged/             # 合并/精炼后的版本
│   ├── 词袋A_合并版.md
│   └── 词袋A_合并版.json
├── tcfd-validated/     # LLM 校验后版本（最终生产用）
│   ├── tcfd_validated.json
│   └── tcfd_unique_validated.json
└── auxiliary/          # 辅助词表
    └── words_bag_b.md
```

## 各版本用途与关系

| 版本 | 维度 | 词数 | 用途 |
|------|------|------|------|
| `raw/词袋A.md` / `.json` | 3 (技术/市场/政策) | ~5300 词（含近义扩展） | **最初**词袋来源，含 math_label 与大量近义词 |
| `raw/words_bag.md` | 3 (技术/市场/政策) | ~200 词 | 旧版三维度简表，给 LLM 抽取时使用 |
| `merged/词袋A_合并版.*` | 3 (技术/市场/政策) | ~5300 词 | 合并精炼后版本（去掉重复） |
| `tcfd-validated/tcfd_validated.json` | 3 (技术/市场/政策) | ~3900 词 | **生产词袋**，LLM 按 TCFD 标准二次过滤 |
| `tcfd-validated/tcfd_unique_validated.json` | 3 (技术/市场/政策) | ~3700 词 | 进一步去重后的版本 |
| `auxiliary/words_bag_b.md` | 1 (负面/风险词) | ~50 词 | 共现分析中 B 类词（风险/波动类） |

## 演变流程

```
raw/词袋A (原始)                    raw/words_bag (旧版简表)
    │                                      │
    │ 合并精炼                            │
    ▼                                      │
merged/词袋A_合并版                        │
    │                                      │
    │ LLM 按 TCFD 标准校验                 │
    ▼                                      │
tcfd-validated/tcfd_validated              │
    │                                      │
    │ 进一步去重                            │
    ▼                                      │
tcfd-validated/tcfd_unique_validated      │
                                           │
                                           │ 在频率统计中作为 A 类词
                                           ▼
                                auxiliary/words_bag_b (B 类词)
```

## 代码引用

| 文件 | 默认引用路径 |
|------|-------------|
| `src/tcfd_extractor/main.py` | `doc/word-bags/raw/words_bag.md` |
| `src/tcfd_extractor/main_simple.py` | `doc/word-bags/raw/words_bag.md` |
| `src/tcfd_extractor/frequency/main.py` | `doc/word-bags/tcfd-validated/tcfd_validated.json`（`--bag-a-file`）<br>`doc/word-bags/auxiliary/words_bag_b.md`（`--bag-b-file`） |
| `scripts/merge_llm_stats.py` | `doc/word-bags/tcfd-validated/tcfd_llm_validated.json` |
| `scripts/resolve_tcfd_duplicates_fast.py` | `doc/word-bags/tcfd-validated/tcfd_validated.json`（输入）<br>`doc/word-bags/tcfd-validated/tcfd_llm_validated.json`（输出） |
| `tests/test_extractor.py` | `doc/word-bags/raw/words_bag.md` |
| `tests/test_integration.py` | `doc/word-bags/raw/words_bag.md` |

## 历史说明

最初所有词袋与分析文件集中在 `doc/plan/` 下，结构混乱、未分类。
2026-06-18 重组为当前 `doc/word-bags/{raw, merged, tcfd-validated, auxiliary}` 四层结构，
分析与文档统一进入 `doc/analysis/` 与 `doc/superpowers/`。
