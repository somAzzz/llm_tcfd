# ECharts 可视化升级实施计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 HR 报告 3 个基础图 (Plotly donut/trend/bar) 替换为 4 个 ECharts 高级交互图 (sunburst/streamgraph/force-directed/sankey), 保留单文件 HTML + CDN 部署模式, 完整移除 Plotly 依赖。

**Architecture:** Python 端为 4 个新数据加载方法 + 4 个 ECharts option builder, 输出 inline JSON 嵌入 HTML; 浏览器端 ECharts 5.5 CDN 解析 JSON 渲染。 4 个图各自独立 try/catch, 单图失败不阻断全页。

**Tech Stack:** Python ≥ 3.12, ECharts 5.5.0 (CDN), Jinja2, Plotly (移除), pytest, uv。

**Worktree:** 不使用, 在 main 分支直接执行。 与上一轮部署决策一致; 任务独立可逆 (build 脚本不入 git, 数据源不变)。

**Spec reference:** `doc/superpowers/specs/2026-06-18-echarts-visualization-upgrade-design.md` (commit `840efbc`)

**Branching model:** 主仓 main 累积 8 commits (上一个 spec 阶段)。 本次新增 commits 追加在 main 之后。

---

## File Structure

| 路径 | 操作 | 责任 |
|---|---|---|
| `src/tcfd_extractor/visualization/echarts.py` | **新建** | TCFD_THEME_CONFIG + _get_base_option() + 4 个 builder |
| `src/tcfd_extractor/visualization/data_loader.py` | **修改** | 新增 load_sunburst/streamgraph/network/sankey_data 4 个方法 |
| `src/tcfd_extractor/visualization/html_assembler.py` | **修改** | 替换 Plotly 调用, 嵌入 4 图 inline JSON |
| `src/tcfd_extractor/visualization/template.py` | **修改** | ECharts CDN + 4 div + per-chart try/catch 渲染块 |
| `src/tcfd_extractor/visualization/chart_builders.py` | **删除** | Plotly 代码全部废弃 |
| `tests/test_visualization/test_echarts.py` | **新建** | 4 builder 骨架断言 + TCFD_THEME_CONFIG 校验 |
| `tests/test_visualization/test_data_loader.py` | **修改** | 4 个新聚合方法单元测试 |
| `tests/test_visualization/test_chart_builders.py` | **删除** | Plotly 测试废弃 |
| `tests/test_visualization/test_html_assembler.py` | **修改** | 集成测试: 4 图 inline `<script>` 存在 |
| `pyproject.toml` | **修改** | 移除 `plotly>=5.0.0` 依赖 |
| `scripts/build_report.py` | **微调** | 注释更新 (输出大小预期) |
| `README.md` | **微调** | HR 报告章节添加 "ECharts 4 个高级图" 说明 |

**净变化**: 新增 2 + 扩展 4 + 修改 4 + 删除 2 ≈ **+800 行, -150 行** (净 +650 行, ~50% 测试)

---

## Chunk 1: data_loader 新增 4 个聚合方法 (TDD)

**Files:**
- Modify: `src/tcfd_extractor/visualization/data_loader.py`
- Modify: `tests/test_visualization/test_data_loader.py`

**目标**: 4 个新方法从源头数据生成各图所需结构, 是后续 builder 的输入。 先写测试, 写实现, 全部跑通再 commit。

### Task 1.1: 扩展测试文件 fixture + load_sunburst_data

**Files:**
- Modify: `tests/test_visualization/test_data_loader.py:1-30` (添加 import + fixture)
- Modify: `src/tcfd_extractor/visualization/data_loader.py` (添加方法)

- [ ] **Step 1: 写 load_sunburst_data 的失败测试**

在 `tests/test_visualization/test_data_loader.py` 末尾添加:

```python
def test_load_sunburst_data_returns_3_dim_tree(tmp_path):
    """Sunburst: 3 维根 → 聚类 → 关键词 三层树。

    真实 cluster JSON 格式: 顶层 list, 每项 {cluster_id, keywords, size, math_label}
    文件名: {政策维度,市场维度,技术维度}_clusters.json
    """
    # 构造最小 cluster JSON (匹配真实 schema)
    clusters_dir = tmp_path / "phase5_category_mapping"
    clusters_dir.mkdir()
    (clusters_dir / "政策维度_clusters.json").write_text(json.dumps([
        {"cluster_id": 0, "math_label": "聚类A", "keywords": ["词1", "词2"], "size": 2},
        {"cluster_id": 1, "math_label": "聚类B", "keywords": ["词3"], "size": 1},
    ], ensure_ascii=False))
    (clusters_dir / "市场维度_clusters.json").write_text(json.dumps([
        {"cluster_id": 0, "math_label": "聚类C", "keywords": ["词4"], "size": 1},
    ], ensure_ascii=False))
    (clusters_dir / "技术维度_clusters.json").write_text(json.dumps([], ensure_ascii=False))

    from tcfd_extractor.visualization.data_loader import load_sunburst_data
    result = load_sunburst_data(clusters_dir)

    assert len(result) == 3  # 3 个 dim 根
    assert result[0]["name"] == "政策"
    assert len(result[0]["children"]) == 2  # 政策有 2 聚类
    assert result[0]["children"][0]["name"] == "聚类A"  # math_label 字段
    # 技术维度 children 应为空列表 (cluster 空)
    assert result[2]["children"] == []
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/test_visualization/test_data_loader.py::test_load_sunburst_data_returns_3_dim_tree -v`
Expected: `ImportError` 或 `ModuleNotFoundError` (load_sunburst_data 尚未定义)

- [ ] **Step 3: 实现 load_sunburst_data (匹配真实 cluster JSON schema)**

在 `src/tcfd_extractor/visualization/data_loader.py` 末尾添加:

```python
def load_sunburst_data(clusters_dir: Path) -> list[dict]:
    """Sunburst 数据: 3 维 → 聚类 → 关键词 三层树。

    真实 cluster JSON 格式: 顶层 list, 每项 {cluster_id, keywords, size, math_label}
    文件名: {政策维度,市场维度,技术维度}_clusters.json

    Args:
        clusters_dir: 含 {政策维度,市场维度,技术维度}_clusters.json 的目录

    Returns:
        list of {name, children: [{name, children: [{name, value}]}]}
    """
    import json as _json
    # 文件名用 "维度" 后缀, 显示名不带
    dim_files = [("政策", "政策维度"), ("市场", "市场维度"), ("技术", "技术维度")]
    result = []
    for display_name, file_stem in dim_files:
        path = clusters_dir / f"{file_stem}_clusters.json"
        if not path.exists():
            logger.warning("Sunburst: cluster file missing for dim=%s (path=%s), skipping",
                           display_name, path)
            result.append({"name": display_name, "children": []})
            continue
        with path.open(encoding="utf-8") as f:
            data = _json.load(f)
        # 真实 schema: 顶层 list, 每项 {cluster_id, math_label, keywords, size}
        if not isinstance(data, list):
            logger.warning("Sunburst: dim=%s file is not a list, skipping", display_name)
            result.append({"name": display_name, "children": []})
            continue
        children = []
        for cluster in data:
            kw_children = [{"name": kw, "value": 1} for kw in cluster.get("keywords", [])]
            children.append({
                "name": cluster.get("math_label", f"cluster_{cluster.get('cluster_id', '?')}"),
                "children": kw_children,
            })
        result.append({"name": display_name, "children": children})
    return result
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/test_visualization/test_data_loader.py::test_load_sunburst_data_returns_3_dim_tree -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tcfd_extractor/visualization/data_loader.py tests/test_visualization/test_data_loader.py
git commit -m "feat(data_loader): load_sunburst_data (3 维 → 聚类 → 关键词 三层树)"
```

### Task 1.2: load_streamgraph_data (TDD)

- [ ] **Step 1: 写失败测试**

```python
def test_load_streamgraph_data_aggregates_dimension_per_year(tmp_path):
    """Streamgraph: 聚合每年 results.jsonl 的 dimension 字段 (is_tcfd_related=true)。"""
    eval_dir = tmp_path / "evaluate_cooccurrence"
    for year, counts in [(2020, {"政策": 5, "市场": 2, "技术": 3}),
                         (2021, {"政策": 7, "市场": 1, "技术": 4})]:
        year_dir = eval_dir / str(year)
        year_dir.mkdir(parents=True)
        rows = []
        for dim, n in counts.items():
            for _ in range(n):
                rows.append({"dimension": dim, "is_tcfd_related": True})
        with (year_dir / "results.jsonl").open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    from tcfd_extractor.visualization.data_loader import load_streamgraph_data
    result = load_streamgraph_data(eval_dir, years=[2020, 2021])

    assert result["years"] == [2020, 2021]
    assert len(result["series"]) == 3  # 3 个 dim
    policy_series = next(s for s in result["series"] if s["name"] == "政策")
    assert policy_series["data"] == [5, 7]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/test_visualization/test_data_loader.py::test_load_streamgraph_data_aggregates_dimension_per_year -v`
Expected: `ImportError`

- [ ] **Step 3: 实现 load_streamgraph_data**

```python
def load_streamgraph_data(eval_dir: Path, years: list[int]) -> dict:
    """Streamgraph: year × 3 维 矩阵。

    Args:
        eval_dir: 含 <year>/results.jsonl 的目录
        years: 年份列表 (e.g., range(2000, 2025))

    Returns:
        {"years": [...], "series": [{"name": "政策", "data": [...]}, ...]}
    """
    import json as _json
    dim_names = ["政策", "市场", "技术"]
    series_data = {d: [] for d in dim_names}
    actual_years = []
    for year in years:
        path = eval_dir / str(year) / "results.jsonl"
        if not path.exists():
            logger.warning("Streamgraph: missing results.jsonl for year=%d", year)
            for d in dim_names:
                series_data[d].append(0)
            actual_years.append(year)
            continue
        counts = {d: 0 for d in dim_names}
        with path.open(encoding="utf-8") as f:
            for line in f:
                row = _json.loads(line)
                if not row.get("is_tcfd_related"):
                    continue
                dim = row.get("dimension", "无")
                if dim in counts:
                    counts[dim] += 1
        for d in dim_names:
            series_data[d].append(counts[d])
        actual_years.append(year)
    return {
        "years": actual_years,
        "series": [{"name": d, "data": series_data[d]} for d in dim_names],
    }
```

- [ ] **Step 4: 跑测试确认通过**

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tcfd_extractor/visualization/data_loader.py tests/test_visualization/test_data_loader.py
git commit -m "feat(data_loader): load_streamgraph_data (year × 3 维 矩阵, 聚合 is_tcfd_related=true)"
```

### Task 1.3: load_network_data (TDD, 重点: 去重 + symbolSize clamp)

- [ ] **Step 1: 写失败测试**

```python
def test_load_network_data_dedupes_and_clamps_symbol_size(tmp_path):
    """Force-directed: 节点去重 + symbolSize clamp [10, 60]。"""
    eval_dir = tmp_path / "evaluate_cooccurrence"
    for year in [2022, 2023]:
        year_dir = eval_dir / str(year)
        year_dir.mkdir(parents=True)
        # 词A 在两条边中出现 → freq=2, symbolSize=10+2*0.5=11
        # 词B 在一条边中出现 → freq=1, symbolSize=10+0.5=10.5→10 (clamp)
        # 词C 极高频 → freq=200, symbolSize clamp 60
        rows = [
            {"keyword_a": "词A", "keyword_b": "词B", "dimension": "政策"},
            {"keyword_a": "词A", "keyword_b": "词C", "dimension": "政策"},
            {"keyword_a": "词B", "keyword_b": "词C", "dimension": "市场"},
        ] + [{"keyword_a": "词A", "keyword_b": "词C", "dimension": "政策"}] * 200  # 让 C 极高频
        with (year_dir / "results.jsonl").open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    from tcfd_extractor.visualization.data_loader import load_network_data
    result = load_network_data(eval_dir, years=[2022, 2023],
                                top_n_edges=100, min_weight=1)

    # 节点 id 唯一
    node_ids = [n["id"] for n in result["nodes"]]
    assert len(node_ids) == len(set(node_ids))

    # symbolSize 在 [10, 60]
    for n in result["nodes"]:
        assert 10 <= n["symbolSize"] <= 60, f"node {n['id']} size {n['symbolSize']} out of range"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/test_visualization/test_data_loader.py::test_load_network_data_dedupes_and_clamps_symbol_size -v`
Expected: `ImportError`

- [ ] **Step 3: 实现 load_network_data**

```python
def load_network_data(eval_dir: Path, years: list[int],
                     top_n_edges: int = 500, min_weight: int = 5) -> dict:
    """Force-directed 网络: 节点去重 + symbolSize clamp。

    Args:
        eval_dir: 含 <year>/results.jsonl 的目录
        years: 年份列表 (近 3 年)
        top_n_edges: 取权重最大的前 N 条边
        min_weight: 边权重阈值 (低于此的边被过滤)

    Returns:
        {"nodes": [{"id", "name", "symbolSize", "category", "value"}],
         "links": [{"source", "target", "weight"}],
         "categories": [{"name": "政策"}]}
    """
    import json as _json
    from collections import Counter, defaultdict
    # 聚合边
    edge_counter = Counter()
    edge_dim = {}  # 边的 dim (取任一端的)
    for year in years:
        path = eval_dir / str(year) / "results.jsonl"
        if not path.exists():
            logger.warning("Network: missing results.jsonl for year=%d", year)
            continue
        with path.open(encoding="utf-8") as f:
            for line in f:
                row = _json.loads(line)
                a, b = row.get("keyword_a"), row.get("keyword_b")
                if not a or not b:
                    continue
                # 规范化: (小词, 大词) 保证无向图唯一
                key = tuple(sorted([a, b]))
                edge_counter[key] += 1
                edge_dim[key] = row.get("dimension", "无")
    # 过滤 + 排序
    edges = [(k, v) for k, v in edge_counter.most_common(top_n_edges) if v >= min_weight]
    if len(edges) < 50:
        # 降阈值重试一次
        edges = [(k, v) for k, v in edge_counter.most_common(top_n_edges)]
    if len(edges) < 50:
        logger.warning("Network: only %d edges after retry, will show subtext warning", len(edges))
    # 节点去重 + freq 统计
    seen = set()
    node_freq = Counter()
    node_dim = {}
    for (a, b), w in edges:
        for kw in (a, b):
            if kw not in seen:
                seen.add(kw)
            node_freq[kw] += 1
            node_dim[kw] = edge_dim.get((a, b), "无")
    # 节点列表
    nodes = []
    for kw in seen:
        size = max(10, min(60, 10 + node_freq[kw] * 0.5))
        nodes.append({
            "id": kw, "name": kw,
            "symbolSize": size,
            "category": node_dim.get(kw, "无"),
            "value": node_freq[kw],
        })
    # 边列表
    links = [{"source": a, "target": b, "weight": w} for (a, b), w in edges]
    return {"nodes": nodes, "links": links}
```

- [ ] **Step 4: 跑测试确认通过**

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tcfd_extractor/visualization/data_loader.py tests/test_visualization/test_data_loader.py
git commit -m "feat(data_loader): load_network_data (去重 + symbolSize clamp [10, 60] + 降阈值重试)"
```

### Task 1.4: load_sankey_data (TDD, 重点: 命名空间前缀)

- [ ] **Step 1: 写失败测试**

```python
def test_load_sankey_data_aggregates_by_year_not_company_year(tmp_path):
    """Sankey: 节点按 year 聚合 (非 company-year), 避免节点爆炸 (3000+ → ~75)。

    真实文件路径硬编码为 output/tcfd_keywords/tcfd_keywords_summary.csv。
    阶段 1/2/3 按年聚合 (25 年 × 3 阶段 = 75 节点), 阶段 4 合并为 3 节点。
    """
    import os
    from tcfd_extractor.visualization.data_loader import load_sankey_data
    # 临时设置 CWD 到 tmp_path 并构造 fake 目录结构
    os.chdir(tmp_path)
    (tmp_path / "output" / "tcfd_keywords").mkdir(parents=True)
    summary_csv = tmp_path / "output" / "tcfd_keywords" / "tcfd_keywords_summary.csv"
    summary_csv.write_text(
        '年报,政策维度,市场维度,技术维度\n'
        '万科A-2023,"碳达峰,碳中和","绿色信贷","余热余能"\n'
        '万科A-2024,"碳达峰","绿色债券","余热余能,绿氢"\n',
        encoding="utf-8"
    )
    (tmp_path / "output" / "evaluate_cooccurrence" / "2023").mkdir(parents=True)
    (tmp_path / "output" / "evaluate_cooccurrence" / "2024").mkdir(parents=True)
    for year in [2023, 2024]:
        with (tmp_path / "output" / "evaluate_cooccurrence" / str(year) / "results.jsonl").open(
            "w", encoding="utf-8"
        ) as f:
            for _ in range(10):
                f.write(json.dumps({"is_tcfd_related": True}, ensure_ascii=False) + "\n")

    result = load_sankey_data(eval_dir=tmp_path / "output" / "evaluate_cooccurrence")

    # 所有节点都有 stage{N}_ 前缀
    for n in result["nodes"]:
        assert n["name"].startswith("stage"), f"node {n['name']} missing stage prefix"
    # 阶段 1/2/3 节点 ≤ 3 年 × 3 阶段 = 9 (不是 1001 × 3 = 3003)
    stage123 = [n for n in result["nodes"]
                if n["name"].startswith("stage1_")
                or n["name"].startswith("stage2_")
                or n["name"].startswith("stage3_")]
    assert len(stage123) <= 9, f"too many stage1-3 nodes: {len(stage123)}"
    # stage4 节点 ≤ 3 (合并)
    stage4 = [n for n in result["nodes"] if n["name"].startswith("stage4_")]
    assert len(stage4) <= 3
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/test_visualization/test_data_loader.py::test_load_sankey_data_aggregates_by_year_not_company_year -v`
Expected: `ImportError`

- [ ] **Step 3: 实现 load_sankey_data (按年聚合, 路径 hardcode)**

```python
def load_sankey_data(eval_dir: Path,
                    summary_csv: Path | None = None,
                    chunk_per_report: int = 150) -> dict:
    """Sankey: 4 阶段流水线, 阶段 1/2/3 按 year 聚合 (避免节点爆炸)。

    真实文件路径 (相对项目根):
        summary_csv = output/tcfd_keywords/tcfd_keywords_summary.csv
        eval_dir    = output/evaluate_cooccurrence/

    Args:
        eval_dir: evaluate_cooccurrence 目录 (用于披露计数)
        summary_csv: 可选覆盖路径, 默认 output/tcfd_keywords/tcfd_keywords_summary.csv
        chunk_per_report: 经验估算 (1 report ≈ 150 chunks, ±50% 误差)

    Returns:
        {"nodes": [{"name": "stage1_report_2023"}, ...],
         "links": [{"source": "...", "target": "...", "value": N}]}
    """
    import csv as _csv
    import json as _json
    from collections import defaultdict
    if summary_csv is None:
        summary_csv = Path("output/tcfd_keywords/tcfd_keywords_summary.csv")
    # 读 summary.csv, 按 year 聚合 (不按 company-year, 避免节点爆炸)
    year_data = {}  # {year: {report_count, policy_keywords, market_keywords, tech_keywords}}
    with summary_csv.open(encoding="utf-8") as f:
        reader = _csv.DictReader(f)
        for row in reader:
            fn = row["年报"]
            # 真实格式: {company_id}-{company_name}-{year}年年度报告.txt
            # 例: 000629-攀钢钢钒-2008年年度报告.txt
            # 倒数第 2 个 "-" 后面是年份
            try:
                # 用 rsplit 找最后一个 "年" 之前的数字
                if "年年度报告" not in fn:
                    continue
                year_str = fn.split("年年度报告")[0].rsplit("-", 1)[-1]
                year = int(year_str)
            except (ValueError, IndexError):
                continue
            if year not in year_data:
                year_data[year] = {
                    "report_count": 0,
                    "policy": set(), "market": set(), "tech": set(),
                }
            year_data[year]["report_count"] += 1
            for dim, key in [("政策维度", "policy"), ("市场维度", "market"), ("技术维度", "tech")]:
                kws = row.get(dim, "")
                for k in kws.split(","):
                    k = k.strip()
                    if k:
                        year_data[year][key].add(k)
    # 阶段 1/2/3 按 year 聚合 (75 节点 = 25 年 × 3 阶段)
    nodes = set()
    links = []
    stage4_value = defaultdict(int)  # dim → total
    for year, data in year_data.items():
        stage1_name = f"stage1_report_{year}"
        stage2_name = f"stage2_chunk_{year}"
        stage3_name = f"stage3_disclosure_{year}"
        nodes.update([stage1_name, stage2_name, stage3_name])
        # 阶段 1 → 2: report_count × chunk_per_report (估算)
        links.append({
            "source": stage1_name, "target": stage2_name,
            "value": data["report_count"] * chunk_per_report,
        })
        # 阶段 2 → 3: 真实披露数 (从 results.jsonl 聚合 is_tcfd_related=true)
        jsonl_path = eval_dir / str(year) / "results.jsonl"
        disclosure_count = 0
        if jsonl_path.exists():
            with jsonl_path.open(encoding="utf-8") as f:
                for line in f:
                    r = _json.loads(line)
                    if r.get("is_tcfd_related"):
                        disclosure_count += 1
        else:
            logger.warning("Sankey: missing results.jsonl for year=%d, using 0", year)
        links.append({
            "source": stage2_name, "target": stage3_name, "value": disclosure_count,
        })
        # 阶段 3 → 4: 按 dim 拆分
        for dim_zh, dim_en in [("policy", "policy"), ("market", "market"), ("tech", "tech")]:
            kw_set = data[dim_en]
            if kw_set:
                stage4_name = f"stage4_dim_{dim_en}"
                value = len(kw_set)
                links.append({
                    "source": stage3_name, "target": stage4_name, "value": value,
                })
                stage4_value[stage4_name] += value
    # 添加 stage4 节点
    for stage4_name in stage4_value:
        nodes.add(stage4_name)
    return {
        "nodes": [{"name": n} for n in sorted(nodes)],
        "links": links,
    }
```

- [ ] **Step 4: 跑测试确认通过**

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tcfd_extractor/visualization/data_loader.py tests/test_visualization/test_data_loader.py
git commit -m "feat(data_loader): load_sankey_data (4 阶段 DAG, stage{N}_ 命名空间, 阶段 2 估算+阶段 3 真实)"
```

### Task 1.5: Chunk 1 集成测试 (跑全部 data_loader 测试)

- [ ] **Step 1: 跑所有 data_loader 测试**

Run: `uv run pytest tests/test_visualization/test_data_loader.py -v`
Expected: 全部 PASS (新增 4 个 + 现有 N 个, 共 ≥ 4)

- [ ] **Step 2: 跑所有 visualization 测试 (回归)**

Run: `uv run pytest tests/test_visualization/ -v`
Expected: 全绿 (chunk 1 还未删 chart_builders, 现有测试还应通过)

- [ ] **Step 3: (无 commit, 进入 Chunk 2)**

---

## Chunk 2: echarts.py 模块 (TCFD_THEME_CONFIG + 4 个 builder + 测试)

**Files:**
- Create: `src/tcfd_extractor/visualization/echarts.py`
- Create: `tests/test_visualization/test_echarts.py`

**目标**: Python 端只生成 ECharts option dict (JSON 序列化), 不做渲染。 4 个 builder 各自接受 data + theme, 返回 option dict。

### Task 2.1: TCFD_THEME_CONFIG + _get_base_option 骨架

- [ ] **Step 1: 创建 echarts.py 含 TCFD_THEME_CONFIG**

Create: `src/tcfd_extractor/visualization/echarts.py`

```python
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
```

- [ ] **Step 2: 创建 test_echarts.py 含 TCFD_THEME_CONFIG 校验**

Create: `tests/test_visualization/test_echarts.py`

```python
"""echarts.py 单元测试: TCFD_THEME_CONFIG + 4 builder 骨架断言。"""
from __future__ import annotations

import pytest

from tcfd_extractor.visualization.echarts import (
    TCFD_THEME_CONFIG,
    _get_base_option,
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
```

- [ ] **Step 3: 跑测试确认通过**

Run: `uv run pytest tests/test_visualization/test_echarts.py -v`
Expected: 4 个测试全 PASS

- [ ] **Step 4: Commit**

```bash
git add src/tcfd_extractor/visualization/echarts.py tests/test_visualization/test_echarts.py
git commit -m "feat(echarts): TCFD_THEME_CONFIG + _get_base_option 骨架 + 主题校验测试"
```

### Task 2.2: build_sunburst (TDD)

- [ ] **Step 1: 在 test_echarts.py 末尾添加 build_sunburst 测试**

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/test_visualization/test_echarts.py::test_build_sunburst_returns_echarts_option_skeleton -v`
Expected: `ImportError: cannot import name 'build_sunburst'`

- [ ] **Step 3: 在 echarts.py 末尾实现 build_sunburst**

```python
def build_sunburst(data: list[dict], theme: dict) -> dict:
    """Sunburst: 3 维 → 聚类 → 关键词 三层树。"""
    opt = _get_base_option("TCFD 维度聚类分布", "点击节点下钻")
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

- [ ] **Step 4: 跑测试确认通过**

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tcfd_extractor/visualization/echarts.py tests/test_visualization/test_echarts.py
git commit -m "feat(echarts): build_sunburst (3 维聚类下钻, ECharts sunburst series)"
```

### Task 2.3: build_streamgraph (TDD)

- [ ] **Step 1: 写测试**

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/test_visualization/test_echarts.py::test_build_streamgraph_returns_stacked_line_series -v`
Expected: `ImportError: cannot import name 'build_streamgraph'`

- [ ] **Step 3: 实现 build_streamgraph**

```python
def build_streamgraph(data: dict, theme: dict) -> dict:
    """Streamgraph: year × 3 维 堆叠流图, dataZoom 缩放。"""
    opt = _get_base_option("TCFD 披露趋势 (2000-2024)", "拖动底部滑块缩放时间区间")
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

- [ ] **Step 4: 跑测试确认通过**

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tcfd_extractor/visualization/echarts.py tests/test_visualization/test_echarts.py
git commit -m "feat(echarts): build_streamgraph (25 年 × 3 维 堆叠流, dataZoom 缩放)"
```

### Task 2.4: build_network (TDD)

- [ ] **Step 1: 写测试**

```python
def test_build_network_returns_force_graph_with_unique_ids():
    """Network builder: graph + force layout, 节点 id 唯一, symbolSize 在 [10, 60]。"""
    data = {
        "nodes": [
            {"id": "词A", "name": "词A", "symbolSize": 15, "category": "政策", "value": 2},
            {"id": "词B", "name": "词B", "symbolSize": 10, "category": "市场", "value": 1},
        ],
        "links": [{"source": "词A", "target": "词B", "weight": 5}],
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
```

- [ ] **Step 2: 跑测试确认失败**

Expected: `ImportError`

- [ ] **Step 3: 实现 build_network**

```python
def build_network(data: dict, theme: dict) -> dict:
    """Force-directed 网络: 节点可拖拽, force layout。"""
    opt = _get_base_option("关键词共现网络 (近 3 年)", "可拖拽节点, hover 显示共现次数")
    n_edges = len(data["links"])
    # 边数过少时, 注入 subtext 提示
    if n_edges < 50:
        opt["title"]["subtext"] = (
            f"⚠️ 当前年份披露数据较少 (仅 {n_edges} 边), "
            "已自动降低关联阈值展示"
        )
        opt["graphic"] = [{
            "type": "text", "left": "center", "top": "middle",
            "style": {"text": f"共 {len(data['nodes'])} 节点, {n_edges} 边",
                      "fontSize": 14, "fill": "#666"},
        }]
    opt["series"] = [{
        "type": "graph",
        "layout": "force",
        "data": data["nodes"],
        "links": data["links"],
        "categories": [{"name": "政策"}, {"name": "市场"}, {"name": "技术"}],
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

- [ ] **Step 4: 跑测试确认通过**

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tcfd_extractor/visualization/echarts.py tests/test_visualization/test_echarts.py
git commit -m "feat(echarts): build_network (force layout, 节点可拖拽, 稀疏时 subtext 提示)"
```

### Task 2.5: build_sankey (TDD)

- [ ] **Step 1: 写测试**

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

Expected: `ImportError`

- [ ] **Step 3: 实现 build_sankey**

```python
def build_sankey(data: dict, theme: dict) -> dict:
    """Sankey: 4 阶段流水线, 节点命名空间前缀, 渲染时剥离。"""
    opt = _get_base_option("NLP 流水线数据提纯",
                          "10,814 份报告 → 分块 → 披露 → 维度归类")
    opt["series"] = [{
        "type": "sankey",
        "data": data["nodes"],
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

- [ ] **Step 4: 跑测试确认通过**

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tcfd_extractor/visualization/echarts.py tests/test_visualization/test_echarts.py
git commit -m "feat(echarts): build_sankey (4 阶段流水线, stage{N}_ 命名空间, formatter 剥离)"
```

### Task 2.6: Chunk 2 集成验证

- [ ] **Step 1: 跑所有 echarts 测试**

Run: `uv run pytest tests/test_visualization/test_echarts.py -v`
Expected: 8 个测试全 PASS (4 theme + 4 builders)

- [ ] **Step 2: 跑所有 visualization 测试 (含 chart_builders 旧测试)**

Run: `uv run pytest tests/test_visualization/ -v`
Expected: 全绿 (chart_builders 还未删)

---

## Chunk 3: html_assembler + template 改造

**Files:**
- Modify: `src/tcfd_extractor/visualization/html_assembler.py`
- Modify: `src/tcfd_extractor/visualization/template.py`
- Modify: `tests/test_visualization/test_html_assembler.py`

**目标**: 让现有 build 流水线调用新的 ECharts builder, 替换 template 里的 Plotly CDN, 加 per-chart try/catch 块。

### Task 3.1: 改写 html_assembler.py 使用 ECharts

- [ ] **Step 1: 阅读当前 html_assembler.py 找 Plotly 调用点**

Run: `grep -n "plotly\|chart_builders\|donut\|trend\|bar" src/tcfd_extractor/visualization/html_assembler.py`
Expected: 找到 import 块和 3 处 figure 调用

- [ ] **Step 2: 替换 import + 添加 4 图组装**

在 `html_assembler.py` 顶部替换 `from .chart_builders import ...` 为:

```python
from .echarts import (
    build_sunburst, build_streamgraph, build_network, build_sankey,
)
from .data_loader import (
    load_sunburst_data, load_streamgraph_data, load_network_data,
)
# load_sankey_data 在本模块内调用 (路径 hardcode, 不传参)
```

(注意: 使用 **相对** import `from .echarts` 保持与现有 `from .data_loader` 一致)

- [ ] **Step 3: 替换 3 处 figure 调用为 4 图 option (含死代码清理)**

定位原 3 处 `build_*_chart(...)` + 3 处 `compute_*` 调用, 全部替换:

```python
# 替换原 donut + trend + bar + 3 个 compute_* 调用:
clusters_dir = Path("output/tcfd_keywords/phase5_category_mapping")
eval_dir = results_root  # results_root 参数就是 evaluate_cooccurrence 目录

sunburst_opt = build_sunburst(load_sunburst_data(clusters_dir), {})
streamgraph_opt = build_streamgraph(
    load_streamgraph_data(eval_dir, years=range(2000, 2025)), {}
)
network_opt = build_network(
    load_network_data(eval_dir, years=[2022, 2023, 2024]), {}
)
# Sankey 路径 hardcode (load_sankey_data 内部默认读 output/tcfd_keywords/tcfd_keywords_summary.csv)
sankey_opt = build_sankey(load_sankey_data(eval_dir=eval_dir), {})

# 4 个 option 序列化为 JSON 字符串 (template 用 {{ xxx_json|safe }} 接收)
import json as _json
sunburst_json = _json.dumps(sunburst_opt, ensure_ascii=False)
streamgraph_json = _json.dumps(streamgraph_opt, ensure_ascii=False)
network_json = _json.dumps(network_opt, ensure_ascii=False)
sankey_json = _json.dumps(sankey_opt, ensure_ascii=False)
```

**死代码清理** (必须执行, 否则 import 警告):
- 删除 `from .data_loader import load_all_results, compute_kpis, compute_dimension_distribution, compute_yearly_counts, compute_top_keyword_pairs, years_with_data` (KPI 不再用)
- 删除 `results = load_all_results(...)`, `kpis_raw = compute_kpis(...)`, `years = years_with_data(...)`, `distribution = compute_dimension_distribution(...)`, `yearly = compute_yearly_counts(...)`, `pairs = compute_top_keyword_pairs(...)` 共 6 行
- 保留 `results_root` 用于 `eval_dir`, 保留 `refactor_bar_b64`, `module_graph_svg`, `refactor_stats`, `build_date` 参数

- [ ] **Step 4: 把 4 个 JSON 字符串传入 template 渲染**

定位 `HTML_TEMPLATE.render(...)` 末尾, 改为:

```python
return HTML_TEMPLATE.render(
    sunburst_json=sunburst_json,
    streamgraph_json=streamgraph_json,
    network_json=network_json,
    sankey_json=sankey_json,
    refactor_b64=refactor_bar_b64,
    module_graph_svg=module_graph_svg,
    refactor_stats=refactor_stats or {},
    build_date=build_date or date.today().isoformat(),
)
```

(删除 `kpis=, donut_json=, trend_json=, bar_json=`)

- [ ] **Step 5: 跑现有 html_assembler 测试**

Run: `uv run pytest tests/test_visualization/test_html_assembler.py -v`
Expected: 失败 (template 还未改) — 没关系, 这是预期的, 继续 Task 3.2

- [ ] **Step 6: Commit (assembler 部分) — 暂不 commit, 等 template 改完一起**

(无 commit, 进入 Task 3.2)

### Task 3.2: 改写 template.py 替换 Plotly → ECharts

- [ ] **Step 1: 读 template.py 找 Plotly CDN 引用和 3 个 chart div**

Run: `grep -n "plotly\|cdn\|<div\|<script" src/tcfd_extractor/visualization/template.py`

- [ ] **Step 2: 替换 Plotly CDN 为 ECharts CDN**

在 `<head>` 块, 替换:
```html
<!-- 旧: -->
<script src="https://cdn.plot.ly/plotly-2.x.min.js"></script>
<!-- 新: -->
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
```

- [ ] **Step 3: 替换 3 个 chart div 为 4 个 ECharts div + per-chart 渲染块**

**先删除 3 个 Plotly chart div** (line 165-221 区域): `<div id="donut-data">`, `<div id="trend-data">`, `<div id="bar-data">` 全部移除。

**再添加 4 个 ECharts chart div**:

```html
<!-- Sunburst -->
<div id="echarts-sunburst" class="echarts-chart" style="width:100%; height:400px;"></div>
<script>
try {
    echarts.init(document.getElementById('echarts-sunburst'))
        .setOption({{ sunburst_json|safe }});
} catch (e) {
    var el = document.getElementById('echarts-sunburst');
    el.innerHTML = '<div style="background:#f0f0f0;color:#666;text-align:center;line-height:400px;">图表渲染失败, 请检查数据格式</div>';
    console.error('Sunburst render failed:', e);
}
</script>

<!-- Streamgraph -->
<div id="echarts-streamgraph" class="echarts-chart" style="width:100%; height:400px;"></div>
<script>
try { echarts.init(document.getElementById('echarts-streamgraph')).setOption({{ streamgraph_json|safe }}); } catch (e) { var el = document.getElementById('echarts-streamgraph'); el.innerHTML = '<div style="background:#f0f0f0;color:#666;text-align:center;line-height:400px;">图表渲染失败</div>'; console.error('Streamgraph:', e); }
</script>

<!-- Network -->
<div id="echarts-network" class="echarts-chart" style="width:100%; height:500px;"></div>
<script>
try { echarts.init(document.getElementById('echarts-network')).setOption({{ network_json|safe }}); } catch (e) { var el = document.getElementById('echarts-network'); el.innerHTML = '<div style="background:#f0f0f0;color:#666;text-align:center;line-height:500px;">图表渲染失败</div>'; console.error('Network:', e); }
</script>

<!-- Sankey -->
<div id="echarts-sankey" class="echarts-chart" style="width:100%; height:400px;"></div>
<script>
try { echarts.init(document.getElementById('echarts-sankey')).setOption({{ sankey_json|safe }}); } catch (e) { var el = document.getElementById('echarts-sankey'); el.innerHTML = '<div style="background:#f0f0f0;color:#666;text-align:center;line-height:400px;">图表渲染失败</div>'; console.error('Sankey:', e); }
</script>
```

(注意: fallback 用 `el.innerHTML = ...` 而非 `el.textContent`, 避免残留 canvas)

- [ ] **Step 4: 跑现有 html_assembler 测试 (现在应该过)**

Run: `uv run pytest tests/test_visualization/test_html_assembler.py -v`
Expected: PASS (template 和 assembler 一致)

- [ ] **Step 5: 添加集成测试 (4 个图 inline `<script>` 存在)**

在 `tests/test_visualization/test_html_assembler.py` 末尾添加:

```python
def test_assembled_html_has_4_echarts_charts(tmp_path):
    """集成测试: 生成的 HTML 含 4 个 ECharts 初始化块。"""
    # 假设 build_report 用法: assemble_html(results_root=..., refactor_bar_b64=..., module_graph_svg=..., refactor_stats=...)
    from tcfd_extractor.visualization.html_assembler import assemble_html
    html = assemble_html(
        results_root=Path("output/evaluate_cooccurrence"),
        refactor_bar_b64="iVBORw0KGgo...",  # 1x1 PNG base64
        module_graph_svg="<svg></svg>",
        refactor_stats={"god_class_before": 0, "god_class_after": 0, "module_count": 0,
                        "total_lines": 0, "test_before": 0, "test_after": 0},
    )
    assert "echarts.init" in html
    # 至少 4 处 echarts.init (sunburst + streamgraph + network + sankey)
    assert html.count("echarts.init") >= 4
    # ECharts CDN 引用
    assert "echarts@5" in html
```

- [ ] **Step 6: 跑测试确认**

Run: `uv run pytest tests/test_visualization/test_html_assembler.py -v`
Expected: 全部 PASS

- [ ] **Step 7: Commit**

```bash
git add src/tcfd_extractor/visualization/html_assembler.py src/tcfd_extractor/visualization/template.py tests/test_visualization/test_html_assembler.py
git commit -m "feat(visualization): html_assembler + template 改用 ECharts (4 图 inline JSON + per-chart try/catch)"
```

---

## Chunk 4: 清理 (删 chart_builders, 移除 plotly 依赖, 更新 README)

**Files:**
- Delete: `src/tcfd_extractor/visualization/chart_builders.py`
- Delete: `tests/test_visualization/test_chart_builders.py`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `scripts/build_report.py` (注释)

### Task 4.1: 确认无任何 import 引用 chart_builders / plotly

- [ ] **Step 1: grep 确认**

Run:
```bash
grep -r "from tcfd_extractor.visualization.chart_builders" src/ tests/ scripts/ 2>/dev/null
grep -r "import plotly" src/ tests/ scripts/ 2>/dev/null
```
Expected: 都返回空 (chunk 3 已替换调用)

- [ ] **Step 2: 若有任何残留, 替换为 echarts 调用 (逐个)**

(若 grep 返回非空, 手动修改并重新跑测试)

### Task 4.2: 删除 chart_builders.py 和 test_chart_builders.py

- [ ] **Step 1: 删除源文件**

Run: `git rm src/tcfd_extractor/visualization/chart_builders.py`

- [ ] **Step 2: 删除测试文件**

Run: `git rm tests/test_visualization/test_chart_builders.py`

### Task 4.3: 移除 pyproject.toml 的 plotly 依赖

- [ ] **Step 1: 编辑 pyproject.toml**

```diff
 dependencies = [
     "openai>=1.0.0",
     ...
-    "matplotlib>=3.7.0",
+    "matplotlib>=3.7.0",
     "numpy>=1.24.0",
     "jinja2>=3.0.0",
     "networkx>=3.0",
-    "plotly>=5.0.0",
 ]
```

(移除 `"plotly>=5.0.0",` 这一行)

- [ ] **Step 2: uv sync**

Run: `uv sync`
Expected: plotly 被卸载, 其它依赖不变

- [ ] **Step 3: 跑所有 visualization 测试**

Run: `uv run pytest tests/test_visualization/ -v`
Expected: 全绿 (chart_builders 已删, 旧测试也删了, 新测试覆盖)

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: 移除 plotly 依赖, 删 chart_builders.py + test_chart_builders.py"
```

### Task 4.4: 修复 README.md 的 tcfd-hr-report 引用漂移

(原任务: 更新 HR 章节加 ECharts 说明; 现扩展: 同时修 3 处 `tcfd-hr-report` 残留, 保持与已部署 URL 一致)

- [ ] **Step 1: 定位 3 处 tcfd-hr-report 引用**

Run: `grep -n "tcfd-hr-report\|<user>" README.md`
Expected: 命中 3 处 (line 253, 256, 364) + 之前已存在的引用

- [ ] **Step 2: 全局替换**

Run:
```bash
sed -i 's|tcfd-hr-report|tcfd-report|g; s|<user>|somAzzz|g' README.md
grep -n "tcfd-hr-report\|<user>" README.md
```
Expected: grep 返回空

- [ ] **Step 3: 在 HR 报告章节加 ECharts 说明 (扩展原 Task 4.4)**

在 `## 可视化报告` 章节, 在原 `build_report.py` 代码块**之前**, 添加:

```markdown
### 高级图表 (ECharts, Stage 1)

- **Sunburst** — 3 维 (政策/市场/技术) 聚类层级下钻
- **Streamgraph** — 2000-2024 年 3 维披露演变, 可拖动时间缩放
- **Force-directed Network** — 近 3 年 (2022-2024) 关键词共现, 节点可拖拽
- **Sankey** — NLP 流水线数据提纯 (10,814 报告 → 维度归类)

底层用 ECharts 5.5 CDN, 单文件 HTML 仍可 (1.5-2MB)。
```

- [ ] **Step 4: 跑 grep 确认无残留 plotly 引用**

Run: `grep -i "plotly" README.md`
Expected: 无输出

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs(README): HR 章节加 ECharts 4 高级图说明 + 修复 tcfd-hr-report 引用漂移 (line 253/256/364)"
```

### Task 4.5: 更新 scripts/build_report.py 注释

- [ ] **Step 1: 找到 size 期望的注释**

Run: `grep -n "size\|3-4MB\|1.5-2MB" scripts/build_report.py`

- [ ] **Step 2: 更新注释 (3-4MB → 1.5-2MB)**

(若 docstring 有 size 期望, 改为 1.5-2MB)

- [ ] **Step 3: Commit**

```bash
git add scripts/build_report.py
git commit -m "docs(build_report): 更新输出 size 预期 (3-4MB → 1.5-2MB)"
```

### Task 4.6: Chunk 4 集成验证

- [ ] **Step 1: 跑全部 visualization 测试**

Run: `uv run pytest tests/test_visualization/ -v`
Expected: 全部 PASS (旧 chart_builders 测试已删, 新 test_echarts + test_data_loader 4 方法 + test_html_assembler 集成 = ≥ 20 test)

- [ ] **Step 2: 跑主仓所有测试 (回归)**

Run: `uv run pytest tests/ --ignore=tests/evaluation -q 2>&1 | tail -20`
Expected: 全绿 (其它模块未受影响)

---

## Chunk 5: 端到端构建 + 部署 + 视觉验证

**Files:** 无新文件, 仅部署脚本 + 验证

### Task 5.1: 跑 build_report.py

- [ ] **Step 1: 跑构建**

Run: `cd /home/bo/projects/python/frequency_analyzer && uv run python scripts/build_report.py --output output/report/ 2>&1 | tee /tmp/build_hr_v2.log`
Expected 关键输出:
- `Building refactor bar chart...`
- `Building module graph SVG...`
- `Assembling HTML...`
- `Wrote output/report/index.html (XXX,XXX chars)` (1.5-2MB 范围)
- `✅ Build complete`
- 退出码 = 0

- [ ] **Step 2: 跑 check_leakage.py 二次验证**

Run: `uv run python scripts/check_leakage.py output/report/index.html 2>&1`
Expected: `✅ Leakage check passed for output/report/index.html`, 退出码 0

- [ ] **Step 3: grep 4 图 init 块存在**

Run: `grep -c "echarts.init" output/report/index.html`
Expected: ≥ 4

- [ ] **Step 4: grep ECharts CDN 引用**

Run: `grep -o "echarts@5\.[0-9.]*[^/]*" output/report/index.html | head -1`
Expected: `echarts@5.5.0`

- [ ] **Step 5: grep 4 个 div id**

Run: `grep -oE "id=\"echarts-(sunburst|streamgraph|network|sankey)\"" output/report/index.html | sort -u`
Expected: 4 个 id 全部命中

- [ ] **Step 6: wc -c 验证大小**

Run: `wc -c output/report/index.html`
Expected: 1,500,000-2,000,000 bytes (1.5-2MB)

### Task 5.2: sed 修复 README.md 模板 (沿用上次部署方案)

- [ ] **Step 1: 跑 sed (跟上次 spec 一致)**

Run:
```bash
sed -i.bak \
  -e 's|tcfd-hr-report|tcfd-report|g' \
  -e 's|<username>|somAzzz|g' \
  output/report/README.md
grep -c "tcfd-hr-report" output/report/README.md && echo "FAIL" || echo "OK"
rm output/report/README.md.bak
```
Expected: `OK`

### Task 5.3: 视觉验证 (本地浏览器)

- [ ] **Step 1: 启动本地 HTTP 服务 (背景)**

Run (in background): `cd /home/bo/projects/python/frequency_analyzer/output/report && python3 -m http.server 8765 &`

- [ ] **Step 2: 用 Playwright 打开页面, 截图, 人工目视检查 4 图**

(使用 webapp-testing skill 或直接 curl 验证)

Run: `curl -s http://localhost:8765/ | grep -oE "(echarts@5|id=\"echarts-[a-z]+\"|setOption)" | sort -u | head -10`
Expected: 4 个 div id + ECharts CDN + setOption 全部出现

- [ ] **Step 3: 关闭本地 HTTP 服务**

Run: `pkill -f "http.server 8765"`

### Task 5.4: 重新部署到 GitHub Pages

- [ ] **Step 1: 检查 README.md 修复成功**

Run: `cat output/report/README.md | grep -E "tcfd-report|somAzzz"`
Expected: 包含 `https://somAzzz.github.io/tcfd-report/` 和 `somAzzz`

- [ ] **Step 2: 在 output/report 中 git init (沿用上次 plan)**

Run:
```bash
cd /home/bo/projects/python/frequency_analyzer
git init output/report
git -C output/report add -A
git -C output/report -c user.email="noreply@github.com" -c user.name="somAzzz" commit -m "init: HR report v2 (ECharts 4 高级图)"
```

- [ ] **Step 3: 推送 (用 gh CLI, 沿用上次 plan)**

Run:
```bash
cd /home/bo/projects/python/frequency_analyzer
git -C output/report remote add upstream https://github.com/somAzzz/tcfd-report.git 2>/dev/null || git -C output/report remote set-url upstream https://github.com/somAzzz/tcfd-report.git
git -C output/report push upstream main --force
```
Expected: `+ abc1234...def5678 main -> main (forced update)`

(注: 不需要 `gh repo edit --delete-branch`, 该 flag 不存在。 `--force` push 直接覆盖 v1 的 commit `5e6646e`)

- [ ] **Step 4: 验证 Pages 配置 (source branch 是 main, path 是 /)**

Run: `gh api repos/somAzzz/tcfd-report/pages --jq '.html_url, "branch=" + .source.branch, "path=" + .source.path, "status=" + .status'`
Expected:
- `https://somazzz.github.io/tcfd-report/`
- `branch=main`
- `path=/`
- `status=built` (或 `building`, 部署后会是 `built`)

若 `branch != main` 或 `path != /`, 用 `gh api -X PATCH repos/somAzzz/tcfd-report/pages -f 'source[branch]=main' -f 'source[path]=/'` 修正。

- [ ] **Step 5: curl 验证线上**

Run: `curl -I -s -o /dev/null -w "HTTP %{http_code}\n" https://somAzzz.github.io/tcfd-report/`
Expected: HTTP 200

### Task 5.5: 视觉验证 4 客观子项 (远程)

- [ ] **Step 1: 远程 sunburst 点击下钻**

Run: `curl -s https://somAzzz.github.io/tcfd-report/ | grep -c "id=\"echarts-sunburst\""`
Expected: 1 (div 存在, 实际下钻需浏览器)

- [ ] **Step 2: 远程 streamgraph 缩放**

Run: `curl -s https://somAzzz.github.io/tcfd-report/ | grep -c "dataZoom"`
Expected: ≥ 1 (dataZoom 控件存在)

- [ ] **Step 3: 远程 network 拖拽**

Run: `curl -s https://somAzzz.github.io/tcfd-report/ | grep -c '"layout":"force"'`
Expected: ≥ 1

- [ ] **Step 4: 远程 sankey adjacency focus**

Run: `curl -s https://somAzzz.github.io/tcfd-report/ | grep -c '"focus":"adjacency"'`
Expected: ≥ 1

- [ ] **Step 5: 整体 HTTP + content check**

Run:
```bash
curl -s -o /tmp/check.html https://somAzzz.github.io/tcfd-report/
grep -c "echarts.init" /tmp/check.html
grep -c "echarts@" /tmp/check.html
wc -c /tmp/check.html
```
Expected: 4+ init blocks, ECharts CDN 引用, 1.5-2MB

- [ ] **Step 6: 清理临时文件**

Run: `rm /tmp/build_hr_v2.log /tmp/check.html`

### Task 5.6: 最终 commit + 报告

- [ ] **Step 1: 跑最终验证脚本**

Run:
```bash
echo "=== 1. plotly 残留 ==="
grep -r "import plotly" src/ 2>/dev/null && echo "❌" || echo "✅"

echo "=== 2. chart_builders 残留 ==="
grep -r "chart_builders" src/ tests/ scripts/ 2>/dev/null && echo "❌" || echo "✅"

echo "=== 3. 测试新增 ==="
uv run pytest tests/test_visualization/ --co -q | wc -l

echo "=== 4. HTML 大小 ==="
wc -c output/report/index.html | awk '{print $1/1024/1024 " MB"}'

echo "=== 5. 4 图 init ==="
grep -c "echarts.init" output/report/index.html

echo "=== 6. 线上 ==="
curl -I -s -o /dev/null -w "HTTP %{http_code}\n" https://somAzzz.github.io/tcfd-report/
```

- [ ] **Step 2: 报告最终状态给用户**

- 部署 URL: `https://somAzzz.github.io/tcfd-report/`
- 4 图: Sunburst / Streamgraph / Network / Sankey 全部上线
- HTML 大小: ~1.5-2MB (vs 之前 123KB+3MB Plotly)
- 测试: ≥ 20 新 test, 全绿
- Plotly: 完全移除 (1 个 module, 1 个 test, pyproject dep)

---

## 已知边界 (Out of Plan)

本计划明确**不做**:

1. ❌ 改 visualization 任何其它模块 (anonymize / module_graph / static_charts / translations)
2. ❌ Stage 2 (UI/UX + Alpine.js + LLM tooltip) — 后续 spec
3. ❌ 重跑任何数据流水线 (cooccurrence / clustering)
4. ❌ 改 build_report.py 的 GitHub 部署流程 (沿用上次 plan 验证过的)
5. ❌ 引入构建工具 (npm/webpack), 保持单文件 + CDN
6. ❌ 把模块图从 Mermaid 迁到 ECharts (Stage 2 决定)
7. ❌ 改 sankey 阶段 2 (chunk) 估算值的精度 (±50% 误差, 后续可接入真实计数)
