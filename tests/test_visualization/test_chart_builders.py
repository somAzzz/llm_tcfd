"""Tests for Plotly chart builders."""
import json

import plotly.graph_objects as go

from tcfd_extractor.visualization.chart_builders import (
    build_donut,
    build_yearly_trend,
    build_top_keyword_bar,
)


class TestBuildDonut:
    def test_returns_plotly_figure(self):
        dist = {"政策": 100, "市场": 80, "技术": 60, "无": 40}
        fig = build_donut(dist)
        assert isinstance(fig, go.Figure)

    def test_english_labels(self):
        dist = {"政策": 10, "市场": 5, "技术": 3, "无": 2}
        fig = build_donut(dist)
        labels = [trace.labels[i] for trace in fig.data for i in range(len(trace.labels))]
        assert "Policy" in labels
        assert "Market" in labels
        assert "Technology" in labels
        assert "Not TCFD" in labels

    def test_serializable_to_json(self):
        dist = {"政策": 10, "市场": 5, "技术": 3, "无": 2}
        fig = build_donut(dist)
        json_str = fig.to_json()
        parsed = json.loads(json_str)
        assert "data" in parsed


class TestBuildYearlyTrend:
    def test_returns_plotly_figure(self):
        yearly = {2020: {"total": 50, "tcfd": 30}, 2021: {"total": 60, "tcfd": 40}}
        fig = build_yearly_trend(yearly)
        assert isinstance(fig, go.Figure)

    def test_two_traces(self):
        yearly = {2020: {"total": 50, "tcfd": 30}, 2021: {"total": 60, "tcfd": 40}}
        fig = build_yearly_trend(yearly)
        assert len(fig.data) == 2

    def test_trace_names_english(self):
        yearly = {2020: {"total": 50, "tcfd": 30}}
        fig = build_yearly_trend(yearly)
        names = [trace.name for trace in fig.data]
        assert any("Total" in n for n in names)
        assert any("TCFD" in n for n in names)


class TestBuildTopKeywordBar:
    def test_returns_plotly_figure(self):
        pairs = [(("碳交易", "低碳"), 100), (("环保", "风险"), 80)]
        fig = build_top_keyword_bar(pairs)
        assert isinstance(fig, go.Figure)

    def test_horizontal_bar(self):
        pairs = [(("碳交易", "低碳"), 100), (("环保", "风险"), 80)]
        fig = build_top_keyword_bar(pairs)
        bar = fig.data[0]
        assert bar.orientation == "h"

    def test_customdata_contains_translation(self):
        pairs = [(("碳交易", "低碳"), 100)]
        fig = build_top_keyword_bar(pairs)
        bar = fig.data[0]
        customdata = bar.customdata
        assert customdata is not None
        assert len(customdata) == 1
