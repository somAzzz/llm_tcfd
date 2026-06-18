"""Plotly chart builders for the HR report."""
from __future__ import annotations

import plotly.graph_objects as go

from .translations import translate

_DIMENSION_EN = {
    "政策": "Policy",
    "市场": "Market",
    "技术": "Technology",
    "无": "Not TCFD",
}


def build_donut(distribution: dict[str, int]) -> go.Figure:
    """Build a donut chart of TCFD dimension distribution."""
    canonical_order = ["政策", "市场", "技术", "无"]
    labels_zh = [d for d in canonical_order if distribution.get(d, 0) > 0]
    values = [distribution.get(d, 0) for d in labels_zh]
    labels_en = [_DIMENSION_EN[d] for d in labels_zh]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels_en,
                values=values,
                hole=0.4,
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>Count: %{value}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title=dict(text="TCFD Dimension Distribution", x=0.5, xanchor="center"),
        showlegend=True,
        margin=dict(t=60, b=20, l=20, r=20),
        height=400,
    )
    return fig


def build_yearly_trend(yearly: dict[int, dict[str, int]]) -> go.Figure:
    """Build a line chart with two traces: total records and TCFD-related records."""
    years = sorted(yearly.keys())
    totals = [yearly[y]["total"] for y in years]
    tcfd = [yearly[y]["tcfd"] for y in years]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=years,
            y=totals,
            mode="lines+markers",
            name="Total Co-occurrences Evaluated",
            line=dict(color="#1f77b4", width=2),
            marker=dict(size=8),
            hovertemplate="<b>%{x}</b><br>Total: %{y}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=tcfd,
            mode="lines+markers",
            name="TCFD-Related Disclosures",
            line=dict(color="#2ca02c", width=2),
            marker=dict(size=8),
            hovertemplate="<b>%{x}</b><br>TCFD: %{y}<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(text="Yearly Trend: Volume & TCFD Coverage", x=0.5, xanchor="center"),
        xaxis=dict(title="Year", tickmode="linear"),
        yaxis=dict(title="Count", rangemode="tozero"),
        hovermode="x unified",
        margin=dict(t=60, b=50, l=60, r=20),
        height=450,
    )
    return fig


def build_top_keyword_bar(
    pairs: list[tuple[tuple[str, str], int]],
) -> go.Figure:
    """Build a horizontal bar chart of top-N keyword pairs with bilingual tooltip."""
    pairs_rev = list(reversed(pairs))
    labels_zh = [f"{ka} + {kb}" for (ka, kb), _ in pairs_rev]
    counts = [count for _, count in pairs_rev]
    customdata = [
        {
            "ka_zh": ka,
            "kb_zh": kb,
            "ka_en": translate(ka),
            "kb_en": translate(kb),
            "count": count,
        }
        for (ka, kb), count in pairs_rev
    ]

    fig = go.Figure(
        data=[
            go.Bar(
                y=labels_zh,
                x=counts,
                orientation="h",
                customdata=customdata,
                marker=dict(color="#ff7f0e"),
                hovertemplate=(
                    "<b>%{customdata.ka_zh}</b> + <b>%{customdata.kb_zh}</b><br>"
                    "(%{customdata.ka_en} + %{customdata.kb_en})<br>"
                    "Occurrences: %{customdata.count}"
                    "<extra></extra>"
                ),
            )
        ]
    )
    fig.update_layout(
        title=dict(text="Top Keyword Pairs (Co-occurrences)", x=0.5, xanchor="center"),
        xaxis=dict(title="Occurrence Count"),
        yaxis=dict(title=""),
        margin=dict(t=60, b=40, l=180, r=20),
        height=max(300, 40 * len(pairs) + 100),
    )
    return fig
