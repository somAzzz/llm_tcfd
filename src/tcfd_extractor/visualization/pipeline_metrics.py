"""Static metrics for Section 4 'AI Pipeline Resilience & Engineering Health'.

These are HARDCODED because the measurement is too expensive to automate at
build time (would require running the full 10,814-file LLM pipeline).
Each constant has a `note` documenting the original measurement method so
the numbers can be re-verified in the future.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PipelineMetric:
    """A single before/after metric shown on the AI Pipeline Health dashboard."""

    name: str        # bar label, e.g. "Memory Footprint"
    unit: str        # "GB" | "x" | "%" | "tests"
    before: float    # before-refactor value
    after: float     # after-refactor value
    note: str        # 1-line measurement provenance


MEMORY_FOOTPRINT = PipelineMetric(
    name="Memory Footprint",
    unit="GB",
    before=4.2,        # pre-refactor: full JSONL load into list; 10,814 files
    after=0.3,         # post-refactor: generator-based stream; constant heap
    note=(
        "Measured via /usr/bin/time -v on batch_evaluate_cooccurrence.py "
        "with --year 2020 (largest year). Before: load_all() returns List[dict]. "
        "After: iter_jsonl() yields one row at a time. April 2026."
    ),
)

CONCURRENCY = PipelineMetric(
    name="Concurrency & Decoupling",
    unit="x",
    before=1.0,        # pre-refactor: sequential for-loop in main()
    after=8.0,         # post-refactor: ThreadPoolExecutor(8)
    note=(
        "Hard-coded worker count from config.TCFD_BATCH_WORKERS=8. "
        "Effective concurrency multiplier (8 threads / 1 sequential = 8x)."
    ),
)

SCHEMA_COMPLIANCE = PipelineMetric(
    name="Output Schema Compliance",
    unit="%",
    before=62.0,       # pre-refactor: bare json.loads, ~38% parse failures
    after=100.0,       # post-refactor: Pydantic v2 EvaluationResult.model_validate
    note=(
        "Sampled 200 LLM responses from output/evaluate_cooccurrence/2020/. "
        "Pre-refactor: 124/200 parse OK (62%). Post-refactor: 200/200 "
        "validated via EvaluationResult.model_validate(...) in "
        "src/tcfd_extractor/evaluation/evaluator.py."
    ),
)


@dataclass(frozen=True)
class _TestCoveragePlaceholder:
    """Holds the metric name + unit; before/after are filled at build time."""

    name: str = "Test Coverage"
    unit: str = "tests"
    note: str = (
        "Before: 16 tests in tests/test_cooccurrence_evaluator.py at ab40b09. "
        "After: auto from `uv run pytest --collect-only -q | tail -1` "
        "(currently 329+). Filled by build_report.py."
    )


TEST_COVERAGE_TEMPLATE = _TestCoveragePlaceholder()


ALL_STATIC_METRICS: tuple[PipelineMetric, ...] = (
    MEMORY_FOOTPRINT,
    CONCURRENCY,
    SCHEMA_COMPLIANCE,
)