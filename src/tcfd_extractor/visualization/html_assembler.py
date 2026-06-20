"""Assembles the final HTML by rendering the Jinja2 template with all data."""
from __future__ import annotations

import dataclasses
import json as _json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .data_loader import (
    compute_kpis,
    load_all_results,
    load_network_data,
    load_sankey_data,
    load_streamgraph_data,
    load_sunburst_data,
    years_with_data,
)
from .echarts import (
    TCFD_THEME_CONFIG,
    build_network,
    build_pipeline_health_dashboard,
    build_sankey,
    build_streamgraph,
    build_sunburst,
    encode_echarts_option,
)
from .template import HTML_TEMPLATE
from .translations import KEYWORD_TRANSLATIONS, translate_smart

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReportDataBundle:
    """Structured data contract between report data loading and HTML rendering."""

    sunburst_json: str
    streamgraph_json: str
    network_json: str
    sankey_json: str
    pipeline_health_dashboard_json: str
    module_graph_json: str
    translate_map_json: str
    context_index_json: str
    report_stats: dict
    refactor_stats: dict


def _fmt_int(value: int) -> str:
    """Format integers for compact KPI display."""
    return f"{value:,}"


def _build_report_stats(results_root: Path, refactor_stats: dict | None) -> dict:
    """Compute public-facing KPI values from loaded evaluation results."""
    results = load_all_results(results_root)
    kpis = compute_kpis(results)
    years = years_with_data(results_root)
    year_range = f"{years[0]}-{years[-1]}" if years else "N/A"
    return {
        "companies": _fmt_int(kpis.get("total_companies", 0)),
        "disclosures": _fmt_int(kpis.get("tcfd_count", 0)),
        "records": _fmt_int(kpis.get("total_records", 0)),
        "year_range": year_range,
        "test_count": _fmt_int((refactor_stats or {}).get("test_after", 0)),
    }


def _dataclass_default(obj):
    """JSON encoder fallback: convert dataclass instances to dicts.

    `build_pipeline_health_dashboard` embeds `PipelineMetric` instances in
    each bar's data payload (used by the tooltip formatter).  Standard
    `json.dumps` cannot serialize them, so we register this `default` to
    turn any dataclass into `dataclasses.asdict(...)`.
    """
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


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
                    r = _json.loads(line)
                except _json.JSONDecodeError:
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
                # Pipeline Sankey edges use stage labels, not keyword labels.
                # Index them separately so link clicks can still show examples.
                dim_display = {
                    "政策": "Policy Keywords",
                    "市场": "Market Keywords",
                    "技术": "Technology Keywords",
                }.get(r.get("dimension", ""))
                pipeline_edges = [
                    (f"Reports {year}", f"Chunks {year}"),
                    (f"Chunks {year}", f"Disclosures {year}"),
                ]
                if dim_display:
                    pipeline_edges.append((f"Disclosures {year}", dim_display))
                for source, target in pipeline_edges:
                    index["sankey"].setdefault(f"{source}->{target}", []).append(entry)
    # 限制每个关键词/边最多 3 条
    for k in index["keywords"]:
        index["keywords"][k] = index["keywords"][k][:3]
    for k in index["sankey"]:
        index["sankey"][k] = index["sankey"][k][:3]
    return index


def build_report_data_bundle(
    results_root: Path,
    *,
    clusters_dir: Path = Path("output/tcfd_keywords/phase5_category_mapping"),
    summary_csv: Path | None = None,
    module_graph_dir: Path = Path("src/tcfd_extractor/evaluation"),
    streamgraph_years: range | list[int] = range(2000, 2025),
    network_years: list[int] | None = None,
    pipeline_metrics: list | None = None,
    refactor_stats: dict | None = None,
) -> ReportDataBundle:
    """Build every data artifact needed by the report template.

    This is the visualization boundary: callers provide paths and metadata,
    and receive a self-contained bundle that can be rendered or tested without
    further filesystem decisions in the template layer.
    """
    eval_dir = results_root
    network_years = network_years or [2022, 2023, 2024]

    sunburst_opt = build_sunburst(load_sunburst_data(clusters_dir), TCFD_THEME_CONFIG)
    streamgraph_opt = build_streamgraph(
        load_streamgraph_data(eval_dir, years=list(streamgraph_years)), TCFD_THEME_CONFIG
    )
    network_opt = build_network(
        load_network_data(eval_dir, years=network_years), TCFD_THEME_CONFIG
    )
    try:
        sankey_opt = build_sankey(
            load_sankey_data(eval_dir=eval_dir, summary_csv=summary_csv),
            TCFD_THEME_CONFIG,
        )
    except (FileNotFoundError, KeyError, ValueError) as e:
        logger.warning("Sankey: load_sankey_data failed (%s: %s), rendering empty sankey",
                       type(e).__name__, e)
        sankey_opt = {"series": [{"type": "sankey", "data": [], "links": []}]}

    from tcfd_extractor.visualization.pipeline_metrics import (
        ALL_STATIC_METRICS, TEST_COVERAGE_TEMPLATE, PipelineMetric,
    )
    from tcfd_extractor.visualization.echarts import build_module_graph
    from tcfd_extractor.visualization.module_graph import discover_module_graph

    if pipeline_metrics is None:
        refactor_stats = refactor_stats or {}
        test_coverage = PipelineMetric(
            name=TEST_COVERAGE_TEMPLATE.name,
            unit=TEST_COVERAGE_TEMPLATE.unit,
            before=refactor_stats.get("test_before", 16),
            after=refactor_stats.get("test_after", 0),
            note=TEST_COVERAGE_TEMPLATE.note,
        )
        pipeline_metrics = [*ALL_STATIC_METRICS, test_coverage]

    dashboard_opt = build_pipeline_health_dashboard(pipeline_metrics, TCFD_THEME_CONFIG)
    module_graph_data = discover_module_graph(module_graph_dir)
    if module_graph_data:
        module_graph_opt = build_module_graph(module_graph_data, TCFD_THEME_CONFIG)
    else:
        module_graph_opt = {"series": [{"type": "graph", "data": [], "links": []}]}

    context_index = build_context_index(eval_dir=eval_dir, years=network_years)

    return ReportDataBundle(
        sunburst_json=_json.dumps(sunburst_opt, ensure_ascii=False),
        streamgraph_json=_json.dumps(streamgraph_opt, ensure_ascii=False),
        network_json=_json.dumps(network_opt, ensure_ascii=False),
        sankey_json=_json.dumps(sankey_opt, ensure_ascii=False),
        pipeline_health_dashboard_json=encode_echarts_option(
            dashboard_opt, default=_dataclass_default,
        ),
        module_graph_json=encode_echarts_option(
            module_graph_opt, default=_dataclass_default,
        ),
        translate_map_json=_json.dumps(KEYWORD_TRANSLATIONS, ensure_ascii=False),
        context_index_json=_json.dumps(context_index, ensure_ascii=False),
        report_stats=_build_report_stats(eval_dir, refactor_stats),
        refactor_stats=refactor_stats or {},
    )


def assemble_html(
    results_root: Path,
    *,
    data_bundle: ReportDataBundle | None = None,
    module_graph_svg: str = "",
    pipeline_metrics: list | None = None,
    refactor_stats: dict | None = None,
    build_date: str | None = None,
) -> str:
    """Load data, build charts, render template. Returns final HTML string.

    Stage 5: 新增 pipeline_health_dashboard (4 个 PipelineMetric) 和
    module_graph (AST 发现的依赖图) 两个 ECharts option, 取代静态 PNG。
    `pipeline_metrics` 默认为 None → assembler 用 ALL_STATIC_METRICS 拼 3 个
    静态指标 + 从 refactor_stats.test_before/after 构造 Test Coverage。

    Stage 2: 注入 __hrTranslateMap (全量 KEYWORD_TRANSLATIONS) 和
    __hrContextIndex (节点 + sankey 边 → context 列表, 限 3 sample)。
    """
    if data_bundle is None:
        data_bundle = build_report_data_bundle(
            results_root=results_root,
            pipeline_metrics=pipeline_metrics,
            refactor_stats=refactor_stats,
        )

    return HTML_TEMPLATE.render(
        sunburst_json=data_bundle.sunburst_json,
        streamgraph_json=data_bundle.streamgraph_json,
        network_json=data_bundle.network_json,
        sankey_json=data_bundle.sankey_json,
        pipeline_health_dashboard_json=data_bundle.pipeline_health_dashboard_json,
        module_graph_json=data_bundle.module_graph_json,
        refactor_stats=data_bundle.refactor_stats,
        report_stats=data_bundle.report_stats,
        build_date=build_date or date.today().isoformat(),
        # Stage 2 注入
        translate_map_json=data_bundle.translate_map_json,
        context_index_json=data_bundle.context_index_json,
    )
