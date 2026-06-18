"""Load 25 years of evaluation results and compute aggregate statistics."""
from __future__ import annotations

import json
import logging
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_YEAR_DIR_RE = re.compile(r"^\d{4}$")


def load_all_results(results_root: Path) -> list[dict]:
    """Load every JSONL record under `results_root/{year}/results.jsonl`."""
    results: list[dict] = []
    if not results_root.exists():
        logger.warning("Results root does not exist: %s", results_root)
        return results

    for year_dir in sorted(results_root.iterdir()):
        if not year_dir.is_dir():
            continue
        if not _YEAR_DIR_RE.match(year_dir.name):
            continue
        year = int(year_dir.name)
        jsonl = year_dir / "results.jsonl"
        if not jsonl.exists():
            continue
        with jsonl.open(encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning(
                        "Skipping malformed line %s:%d: %s",
                        jsonl, line_no, line[:100],
                    )
                    continue
                record["_year"] = year
                results.append(record)
    return results


def years_with_data(results_root: Path) -> list[int]:
    """Return sorted list of year integers that have a results.jsonl."""
    if not results_root.exists():
        return []
    years: list[int] = []
    for year_dir in sorted(results_root.iterdir()):
        if year_dir.is_dir() and _YEAR_DIR_RE.match(year_dir.name):
            if (year_dir / "results.jsonl").exists():
                years.append(int(year_dir.name))
    return years


def _extract_company_id(file_field: str) -> str:
    """Extract the leading company_id from a filename."""
    if not file_field:
        return "unknown"
    base = file_field.split("/")[-1]
    parts = base.split("-", 1)
    return parts[0] if parts else "unknown"


def compute_kpis(results: list[dict]) -> dict[str, Any]:
    """Compute top-line KPIs from the loaded results."""
    if not results:
        return {"total_records": 0, "tcfd_count": 0, "total_companies": 0}
    tcfd_count = sum(1 for r in results if r.get("is_tcfd_related"))
    company_ids = {_extract_company_id(r.get("file", "")) for r in results}
    return {
        "total_records": len(results),
        "tcfd_count": tcfd_count,
        "total_companies": len(company_ids),
    }


def compute_dimension_distribution(results: list[dict]) -> dict[str, int]:
    """Count records by `dimension` field. Always returns all 4 keys."""
    counts: Counter = Counter()
    for r in results:
        dim = r.get("dimension", "无")
        if dim:
            counts[dim] += 1
    for d in ("政策", "市场", "技术", "无"):
        if d not in counts:
            counts[d] = 0
    return dict(counts)


def compute_yearly_counts(results: list[dict]) -> dict[int, dict[str, int]]:
    """Aggregate total and TCFD counts per year."""
    agg: dict[int, dict[str, int]] = defaultdict(lambda: {"total": 0, "tcfd": 0})
    for r in results:
        year = r["_year"]
        agg[year]["total"] += 1
        if r.get("is_tcfd_related"):
            agg[year]["tcfd"] += 1
    return dict(sorted(agg.items()))


def compute_top_keyword_pairs(
    results: list[dict], n: int = 10
) -> list[tuple[str, int]]:
    """Return the top-N most frequent (keyword_a + keyword_b) pairs."""
    pair_counts: Counter = Counter()
    for r in results:
        ka = r.get("keyword_a", "").strip()
        kb = r.get("keyword_b", "").strip()
        if ka and kb:
            pair_counts[(ka, kb)] += 1
    return pair_counts.most_common(n)


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
    from collections import Counter
    # 聚合边
    edge_counter: Counter = Counter()
    edge_dim: dict[tuple[str, str], str] = {}  # 边的 dim (取任一端的)
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
    seen: set[str] = set()
    node_freq: Counter = Counter()
    node_dim: dict[str, str] = {}
    for (a, b), _w in edges:
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
