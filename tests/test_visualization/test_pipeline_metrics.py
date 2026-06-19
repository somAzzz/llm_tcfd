"""Tests for the Section 4 AI Pipeline metrics dataclass."""
from __future__ import annotations

import pytest

from tcfd_extractor.visualization.pipeline_metrics import (
    ALL_STATIC_METRICS,
    CONCURRENCY,
    MEMORY_FOOTPRINT,
    PipelineMetric,
    SCHEMA_COMPLIANCE,
    TEST_COVERAGE_TEMPLATE,
)


def test_all_static_metrics_count_is_three():
    assert len(ALL_STATIC_METRICS) == 3


@pytest.mark.parametrize("metric", [MEMORY_FOOTPRINT, CONCURRENCY, SCHEMA_COMPLIANCE])
def test_required_fields_present(metric: PipelineMetric):
    assert metric.name
    assert metric.unit
    assert metric.note
    assert metric.before > 0
    assert metric.after > 0


@pytest.mark.parametrize("metric", [MEMORY_FOOTPRINT, CONCURRENCY, SCHEMA_COMPLIANCE])
def test_metric_unit_in_allowed_set(metric: PipelineMetric):
    assert metric.unit in {"GB", "x", "%", "tests"}


@pytest.mark.parametrize("metric", [MEMORY_FOOTPRINT, CONCURRENCY, SCHEMA_COMPLIANCE])
def test_metric_is_immutable(metric: PipelineMetric):
    with pytest.raises(Exception):
        metric.before = 999.0  # type: ignore[misc]


def test_test_coverage_template_has_expected_metadata():
    assert TEST_COVERAGE_TEMPLATE.name == "Test Coverage"
    assert TEST_COVERAGE_TEMPLATE.unit == "tests"
    assert "16 tests" in TEST_COVERAGE_TEMPLATE.note
    assert "329" in TEST_COVERAGE_TEMPLATE.note