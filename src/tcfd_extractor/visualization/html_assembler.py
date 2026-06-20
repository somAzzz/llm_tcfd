"""Assembles the final HTML by rendering the Jinja2 template with all data."""
from __future__ import annotations

import dataclasses
import json as _json
import logging
from collections import Counter
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
from .translations import display_chart_label, translate_chart_label

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
    insights: list[dict]
    chart_insights: dict[str, list[dict]]
    top_pairs: list[dict]
    refactor_stats: dict


def _fmt_int(value: int) -> str:
    """Format integers for compact KPI display."""
    return f"{value:,}"


def _pct(part: int, total: int) -> str:
    """Format a percentage without noisy decimals."""
    if total <= 0:
        return "0%"
    return f"{part / total:.0%}"


def _tcfd_results(results: list[dict]) -> list[dict]:
    return [r for r in results if r.get("is_tcfd_related")]


def _build_report_stats(
    results_root: Path,
    refactor_stats: dict | None,
    results: list[dict] | None = None,
) -> dict:
    """Compute public-facing KPI values from loaded evaluation results."""
    results = results if results is not None else load_all_results(results_root)
    kpis = compute_kpis(results)
    years = years_with_data(results_root)
    year_range = f"{years[0]}-{years[-1]}" if years else "N/A"
    return {
        "companies": _fmt_int(kpis.get("total_companies", 0)),
        "disclosures": _fmt_int(kpis.get("tcfd_count", 0)),
        "records": _fmt_int(kpis.get("total_records", 0)),
        "years": _fmt_int(len(years)),
        "year_range": year_range,
        "test_count": _fmt_int((refactor_stats or {}).get("test_after", 0)),
    }


def build_portfolio_insights(results: list[dict]) -> list[dict]:
    """Build high-signal insight cards for the portfolio landing view."""
    tcfd = _tcfd_results(results)
    if not tcfd:
        return []

    year_counts: Counter = Counter(r.get("_year") for r in tcfd if r.get("_year"))
    dim_counts: Counter = Counter(r.get("dimension") or "N/A" for r in tcfd)
    first_year = min(year_counts) if year_counts else None
    last_year = max(year_counts) if year_counts else None
    recent_years = [y for y in range((last_year or 0) - 4, (last_year or 0) + 1)]
    recent_total = sum(year_counts[y] for y in recent_years)
    total = len(tcfd)
    policy = dim_counts.get("政策", 0)
    tech = dim_counts.get("技术", 0)
    market = dim_counts.get("市场", 0)

    insights = []
    if first_year and last_year:
        insights.append({
            "label": "Disclosure acceleration",
            "value": f"{_fmt_int(year_counts[first_year])} -> {_fmt_int(year_counts[last_year])}",
            "detail": (
                f"TCFD-related disclosures grew from {first_year} to {last_year}; "
                f"the latest five years account for {_pct(recent_total, total)} of all detected disclosures."
            ),
        })
    insights.append({
        "label": "Policy-led signal",
        "value": _fmt_int(policy),
        "detail": (
            "Policy and compliance language is the dominant disclosure pattern, "
            f"while technology signals contribute {_fmt_int(tech)} mentions and market signals {_fmt_int(market)}."
        ),
    })
    insights.append({
        "label": "Engineering proof",
        "value": "Local LLM + tests",
        "detail": (
            "The report is generated from a reproducible pipeline: streaming JSONL loading, "
            "structured validation, leakage checks, and an automated test suite."
        ),
    })
    return insights


def build_top_keyword_pairs(results: list[dict], limit: int = 5) -> list[dict]:
    """Return top co-occurring keyword pairs for a readable evidence panel."""
    pair_counts: Counter = Counter()
    for r in _tcfd_results(results):
        a = (r.get("keyword_a") or "").strip()
        b = (r.get("keyword_b") or "").strip()
        if not a or not b:
            continue
        pair_counts[tuple(sorted([a, b]))] += 1
    return [
        {
            "pair": f"{display_chart_label(a)} / {display_chart_label(b)}",
            "full_pair": f"{translate_chart_label(a)} / {translate_chart_label(b)}",
            "translated": _describe_keyword_pair(a, b, count),
            "count": _fmt_int(count),
        }
        for (a, b), count in pair_counts.most_common(limit)
    ]


def _describe_keyword_pair(keyword_a: str, keyword_b: str, count: int) -> str:
    """Write a compact interpretation for a ranked keyword pair."""
    a = translate_chart_label(keyword_a)
    b = translate_chart_label(keyword_b)
    joined = f"{a} {b}".lower()
    if any(term in joined for term in ("penalty", "fine", "law", "regulation", "standard", "compliance")):
        signal = "compliance and regulatory pressure"
    elif any(term in joined for term in ("energy", "carbon", "emission", "renewable", "low-carbon")):
        signal = "transition and decarbonization activity"
    elif any(term in joined for term in ("cost", "price", "market", "finance", "subsidy", "volatility")):
        signal = "market and financial exposure"
    elif any(term in joined for term in ("risk", "pressure", "challenge", "loss", "shortage")):
        signal = "risk language in management discussion"
    else:
        signal = "recurring climate-disclosure language"
    return f"{_fmt_int(count)} records link this pair as {signal}."


def build_chart_insights(results: list[dict], top_pairs: list[dict]) -> dict[str, list[dict]]:
    """Create fixed, reader-facing insight callouts for the main charts."""
    tcfd = _tcfd_results(results)
    year_counts: Counter = Counter(r.get("_year") for r in tcfd if r.get("_year"))
    dim_counts: Counter = Counter(r.get("dimension") or "N/A" for r in tcfd)
    total = len(tcfd)
    first_year = min(year_counts) if year_counts else None
    last_year = max(year_counts) if year_counts else None
    recent_total = 0
    if last_year:
        recent_total = sum(year_counts[y] for y in range(last_year - 4, last_year + 1))
    policy = dim_counts.get("政策", 0)
    market = dim_counts.get("市场", 0)
    tech = dim_counts.get("技术", 0)
    top_pair = top_pairs[0]["full_pair"] if top_pairs else "the highest-frequency term pair"

    trend_detail = (
        f"The latest five years contain {_pct(recent_total, total)} of detected disclosures."
        if total else "The trend view summarizes disclosures across the available years."
    )
    if first_year and last_year:
        trend_detail = (
            f"Detected disclosures rise from {_fmt_int(year_counts[first_year])} in "
            f"{first_year} to {_fmt_int(year_counts[last_year])} in {last_year}. "
            f"{trend_detail}"
        )

    return {
        "sunburst": [
            {
                "label": "Dominant layer",
                "value": "Policy-first",
                "detail": (
                    f"Policy language contributes {_fmt_int(policy)} disclosures, "
                    "making compliance the clearest entry point into the taxonomy."
                ),
            },
            {
                "label": "Transition layer",
                "value": _fmt_int(tech),
                "detail": "Technology terms cluster around efficiency, energy substitution, and operational retrofit.",
            },
            {
                "label": "Market layer",
                "value": _fmt_int(market),
                "detail": "Market signals are smaller but connect risk language to price, finance, and volatility.",
            },
        ],
        "streamgraph": [
            {
                "label": "Temporal signature",
                "value": "Post-2020 surge",
                "detail": trend_detail,
            },
            {
                "label": "Dimension balance",
                "value": "Policy / Tech / Market",
                "detail": (
                    f"{_fmt_int(policy)} policy, {_fmt_int(tech)} technology, "
                    f"and {_fmt_int(market)} market disclosures are visible in the evaluated set."
                ),
            },
        ],
        "network": [
            {
                "label": "Core pair",
                "value": top_pair,
                "detail": "The most repeated co-occurrence anchors the recent disclosure vocabulary.",
            },
            {
                "label": "How to read it",
                "value": "Dense center, specific edges",
                "detail": "Large nodes are recurring terms; edges show which concepts companies discuss together.",
            },
        ],
    }


def _build_anonymized_evidence_summary(record: dict, year: int, context: str) -> str:
    """Summarize evidence without publishing raw Chinese report text."""
    keyword_a = translate_chart_label(record.get("keyword_a", ""))
    keyword_b = translate_chart_label(record.get("keyword_b", ""))
    dimension = translate_chart_label(record.get("dimension", ""))
    context_size = len(context)
    if dimension == "Policy":
        frame = "a compliance or regulatory disclosure signal"
    elif dimension == "Market":
        frame = "a market-exposure disclosure signal"
    elif dimension == "Technology":
        frame = "a transition-technology disclosure signal"
    else:
        frame = "a climate-disclosure signal"
    return (
        f"An anonymized {year} filing links {keyword_a} with {keyword_b} as "
        f"{frame}. The public case file withholds the original excerpt; "
        f"the local pipeline evaluated a {context_size}-character source passage."
    )


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
                    "id": f"{year}-sample-{line_no}",
                    "original": "Original excerpt withheld for the public portfolio view.",
                    "translated": _build_anonymized_evidence_summary(r, year, ctx),
                    "source": "Anonymized annual report",
                    "year": year,
                    "dimension": translate_chart_label(r.get("dimension", "")),
                }
                # 关键词索引 (供 network 节点 click)
                for kw in (r.get("keyword_a", ""), r.get("keyword_b", "")):
                    if kw:
                        full_label = translate_chart_label(kw)
                        labels = {full_label, display_chart_label(kw)}
                        for label in labels:
                            index["keywords"].setdefault(label, []).append(entry)
                # Sankey 边索引 (供 sankey 流道 click)
                ka = r.get("keyword_a", "")
                kb = r.get("keyword_b", "")
                if ka and kb:
                    pair = sorted([translate_chart_label(ka), translate_chart_label(kb)])
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
    all_results = load_all_results(eval_dir)

    top_pairs = build_top_keyword_pairs(all_results)

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
        translate_map_json="{}",
        context_index_json=_json.dumps(context_index, ensure_ascii=False),
        report_stats=_build_report_stats(eval_dir, refactor_stats, all_results),
        insights=build_portfolio_insights(all_results),
        chart_insights=build_chart_insights(all_results, top_pairs),
        top_pairs=top_pairs,
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
        insights=data_bundle.insights,
        chart_insights=data_bundle.chart_insights,
        top_pairs=data_bundle.top_pairs,
        build_date=build_date or date.today().isoformat(),
        # Stage 2 注入
        translate_map_json=data_bundle.translate_map_json,
        context_index_json=data_bundle.context_index_json,
    )
