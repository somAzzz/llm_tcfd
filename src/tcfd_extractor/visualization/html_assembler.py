"""Assembles the final HTML by rendering the Jinja2 template with all data."""
from __future__ import annotations

import json as _json
import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

from .data_loader import (
    load_network_data,
    load_sankey_data,
    load_streamgraph_data,
    load_sunburst_data,
)
from .echarts import (
    TCFD_THEME_CONFIG,
    build_network,
    build_sankey,
    build_streamgraph,
    build_sunburst,
)
from .template import HTML_TEMPLATE
from .translations import KEYWORD_TRANSLATIONS, translate_smart


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
    # 限制每个关键词/边最多 3 条
    for k in index["keywords"]:
        index["keywords"][k] = index["keywords"][k][:3]
    for k in index["sankey"]:
        index["sankey"][k] = index["sankey"][k][:3]
    return index


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
    eval_dir = results_root  # results_root 就是 evaluate_cooccurrence 目录

    sunburst_opt = build_sunburst(load_sunburst_data(clusters_dir), TCFD_THEME_CONFIG)
    streamgraph_opt = build_streamgraph(
        load_streamgraph_data(eval_dir, years=range(2000, 2025)), TCFD_THEME_CONFIG
    )
    network_opt = build_network(
        load_network_data(eval_dir, years=[2022, 2023, 2024]), TCFD_THEME_CONFIG
    )
    # Sankey 路径 hardcode (load_sankey_data 内部默认读 output/tcfd_keywords/tcfd_keywords_summary.csv)
    # 若数据缺失则降级为占位 option, 不阻塞 HTML 渲染
    try:
        sankey_opt = build_sankey(load_sankey_data(eval_dir=eval_dir), TCFD_THEME_CONFIG)
    except (FileNotFoundError, KeyError, ValueError) as e:
        logger.warning("Sankey: load_sankey_data failed (%s: %s), rendering empty sankey",
                       type(e).__name__, e)
        sankey_opt = {"series": [{"type": "sankey", "data": [], "links": []}]}

    # 4 个 option 序列化为 JSON 字符串 (template 用 {{ xxx_json|safe }} 接收)
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
