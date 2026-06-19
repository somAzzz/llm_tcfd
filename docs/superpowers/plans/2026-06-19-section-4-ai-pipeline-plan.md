# Section 4 AI Pipeline Resilience Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing "Section 4: Engineering excellence" in the HR report with a new "Robust AI Pipeline Engineering" section featuring an ECharts dashboard titled "AI Pipeline Resilience & Engineering Health" with 4 grouped before/after metrics (Memory Footprint, Concurrency & Decoupling, Output Schema Compliance, Test Coverage), a 3-card narrative column, and a hidden module dependency graph revealed by clicking any bar.

**Architecture:** Surgical replacement (Approach A from the spec). Reuse the existing ECharts dashboard infrastructure (palette, `_get_base_option`, `applyTheme`, AST-discovered module graph). New `pipeline_metrics.py` introduces a `PipelineMetric` dataclass with 3 hardcoded metrics + 1 dynamic (test count). Old `build_refactor_dashboard`, `build_refactor_bar`, `_build_refactor_dashboard_data`, `bindDashboardClickHandler`, `window.__hrAppState`, `x-data="{ showGraph: false }"` are removed and replaced with a clean Alpine-store-based deep-dive flow.

**Tech Stack:** Python 3.12, ECharts 5.5.0 (CDN), Alpine.js 3.13.5 (CDN), Pydantic v2 (existing), Jinja2 (existing), pytest (existing), `git`.

**Parent spec:** `docs/superpowers/specs/2026-06-19-section-4-ai-pipeline-design.md` (commit `08fb789`)

---

## File Structure

### Create
- `src/tcfd_extractor/visualization/pipeline_metrics.py` — `PipelineMetric` dataclass + 3 hardcoded metrics + test-coverage template
- `tests/test_visualization/test_pipeline_metrics.py` — 5 tests for metric invariants

### Modify
- `src/tcfd_extractor/visualization/echarts.py` — Rename builder; add 3 JS formatter constants; integrate with `_get_base_option(theme)`
- `src/tcfd_extractor/visualization/template.py` — Replace Section 4 HTML/CSS/JS
- `src/tcfd_extractor/visualization/html_assembler.py` — Drop `refactor_bar_b64` kwarg + `_build_refactor_dashboard_data`; render new dashboard key
- `src/tcfd_extractor/visualization/static_charts.py` — Remove `build_refactor_bar`
- `scripts/build_report.py` — Remove old metric plumbing; pass metrics list to new builder

### Modify (tests only)
- `tests/test_visualization/test_echarts.py` — Replace `TestRefactorDashboard` with `TestPipelineHealthDashboard`
- `tests/test_visualization/test_html_assembler.py` — Update assertions
- `tests/test_visualization/test_static_charts.py` — Drop `TestBuildRefactorBar`

---

## Chunk 1: Metric dataclass + ECharts builder + Alpine wiring

### Task 1: Create `pipeline_metrics.py` with `PipelineMetric` dataclass and 3 hardcoded metrics

**Files:**
- Create: `src/tcfd_extractor/visualization/pipeline_metrics.py`
- Test: `tests/test_visualization/test_pipeline_metrics.py`

- [ ] **Step 1.1: Write the failing test file**

Create `tests/test_visualization/test_pipeline_metrics.py`:

```python
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
```

- [ ] **Step 1.2: Run the tests to verify they all fail (module does not exist yet)**

Run: `PYTHONPATH=src uv run pytest tests/test_visualization/test_pipeline_metrics.py -v`
Expected: ImportError on `tcfd_extractor.visualization.pipeline_metrics`

- [ ] **Step 1.3: Write the minimal implementation**

Create `src/tcfd_extractor/visualization/pipeline_metrics.py`:

```python
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
```

- [ ] **Step 1.4: Run the tests to verify they pass**

Run: `PYTHONPATH=src uv run pytest tests/test_visualization/test_pipeline_metrics.py -v`
Expected: 9 passing tests (3 parametrized × 3 + 2 standalone). All PASS.

- [ ] **Step 1.5: Commit**

```bash
git add src/tcfd_extractor/visualization/pipeline_metrics.py tests/test_visualization/test_pipeline_metrics.py
git commit -m "feat(metrics): Stage 5.1 — PipelineMetric dataclass + 3 hardcoded metrics"
```

---

### Task 2: Add `build_pipeline_health_dashboard` to `echarts.py`

**Files:**
- Modify: `src/tcfd_extractor/visualization/echarts.py:325-` (replaces `build_refactor_dashboard`)
- Modify: `tests/test_visualization/test_echarts.py:646-721` (replaces `TestRefactorDashboard`)

- [ ] **Step 2.1: Write the failing tests**

Replace `TestRefactorDashboard` in `tests/test_visualization/test_echarts.py` (lines 646-721) with the new class. First, find and read the exact existing block:

Run: `sed -n '640,725p' tests/test_visualization/test_echarts.py`

Then replace the entire `TestRefactorDashboard` class with:

```python
class TestPipelineHealthDashboard:
    """Tests for the Section 4 AI Pipeline Resilience dashboard (8 tests)."""

    @staticmethod
    def _metrics():
        from tcfd_extractor.visualization.pipeline_metrics import (
            ALL_STATIC_METRICS, TEST_COVERAGE_TEMPLATE, PipelineMetric,
        )
        test_coverage = PipelineMetric(
            name=TEST_COVERAGE_TEMPLATE.name,
            unit=TEST_COVERAGE_TEMPLATE.unit,
            before=16,
            after=329,
            note=TEST_COVERAGE_TEMPLATE.note,
        )
        return (*ALL_STATIC_METRICS, test_coverage)

    def test_title_text_matches(self):
        from tcfd_extractor.visualization.echarts import build_pipeline_health_dashboard
        opt = build_pipeline_health_dashboard(self._metrics(), TCFD_THEME_CONFIG)
        assert opt["title"]["text"] == "AI Pipeline Resilience & Engineering Health"

    def test_x_axis_has_four_metric_names(self):
        from tcfd_extractor.visualization.echarts import build_pipeline_health_dashboard
        opt = build_pipeline_health_dashboard(self._metrics(), TCFD_THEME_CONFIG)
        assert opt["xAxis"]["data"] == [
            "Memory Footprint", "Concurrency & Decoupling",
            "Output Schema Compliance", "Test Coverage",
        ]

    def test_two_series_with_correct_colors(self):
        from tcfd_extractor.visualization.echarts import build_pipeline_health_dashboard
        opt = build_pipeline_health_dashboard(self._metrics(), TCFD_THEME_CONFIG)
        assert opt["color"] == ["#8b3a3a", "#56d364"]

    def test_y_axis_hidden(self):
        from tcfd_extractor.visualization.echarts import build_pipeline_health_dashboard
        opt = build_pipeline_health_dashboard(self._metrics(), TCFD_THEME_CONFIG)
        assert opt["yAxis"]["show"] is False

    def test_bar_label_shows_with_formatter(self):
        from tcfd_extractor.visualization.echarts import build_pipeline_health_dashboard
        opt = build_pipeline_health_dashboard(self._metrics(), TCFD_THEME_CONFIG)
        for s in opt["series"]:
            assert s["label"]["show"] is True
            assert s["label"]["position"] == "top"
            assert "formatter" in s["label"]

    def test_tooltip_formatter_present(self):
        from tcfd_extractor.visualization.echarts import build_pipeline_health_dashboard
        opt = build_pipeline_health_dashboard(self._metrics(), TCFD_THEME_CONFIG)
        assert "formatter" in opt["tooltip"]
        assert opt["tooltip"]["trigger"] == "axis"

    def test_each_bar_data_carries_metric_for_tooltip(self):
        from tcfd_extractor.visualization.echarts import build_pipeline_health_dashboard
        metrics = self._metrics()
        opt = build_pipeline_health_dashboard(metrics, TCFD_THEME_CONFIG)
        for series in opt["series"]:
            for datum, m in zip(series["data"], metrics):
                assert datum["metric"] is m
                assert datum["value"] in (m.before, m.after)

    def test_legend_lists_before_and_after(self):
        from tcfd_extractor.visualization.echarts import build_pipeline_health_dashboard
        opt = build_pipeline_health_dashboard(self._metrics(), TCFD_THEME_CONFIG)
        assert opt["legend"]["data"] == ["Before (god-class)", "After (refactored)"]
```

(8 tests, matching the spec §5.6 count.)

Also remove `class TestRefactorDashboard` (the old block) so no two classes with overlapping names exist.

- [ ] **Step 2.2: Run the new tests to verify they all fail**

Run: `PYTHONPATH=src uv run pytest tests/test_visualization/test_echarts.py::TestPipelineHealthDashboard -v`
Expected: ImportError or AttributeError on `build_pipeline_health_dashboard` (the old `build_refactor_dashboard` still exists).

- [ ] **Step 2.3: Replace `build_refactor_dashboard` in `echarts.py`**

Open `src/tcfd_extractor/visualization/echarts.py`. Find the line that starts `def build_refactor_dashboard(` (around line 325) and read it. Replace the **entire function** (signature + body) with:

```python
def build_pipeline_health_dashboard(
    metrics: list["PipelineMetric"],
    theme: dict,
) -> dict:
    """Build the AI Pipeline Resilience & Engineering Health ECharts option.

    Each metric becomes a grouped bar pair (Before / After).
    Y-axis is hidden; per-bar label shows formatted value with unit.
    Inherits `_get_base_option()` styling (chart background, text style,
    animation) so the dashboard participates in the `applyTheme()` cycle
    used by the other 4 ECharts dashboards in the report.
    """
    from tcfd_extractor.visualization.pipeline_metrics import PipelineMetric

    metrics = list(metrics)  # accept any iterable
    bar_labels = [m.name for m in metrics]
    before_vals = [m.before for m in metrics]
    after_vals = [m.after for m in metrics]

    opt = _get_base_option(
        "AI Pipeline Resilience & Engineering Health",
        "Click any bar to view the module graph",
    )
    opt["title"]["left"] = "center"
    opt["title"]["textStyle"] = {
        **theme.get("text_style", {}),
        "fontWeight": 600,
        "fontSize": 16,
    }
    opt["tooltip"] = {
        "trigger": "axis",
        "axisPointer": {"type": "shadow"},
        "formatter": _PIPELINE_HEALTH_TOOLTIP_FN,
    }
    opt["legend"] = {
        "data": ["Before (god-class)", "After (refactored)"],
        "top": 32,
        "textStyle": theme.get("text_style", {}),
    }
    opt["grid"] = {"left": 50, "right": 30, "top": 80, "bottom": 50}
    opt["xAxis"] = {
        "type": "category",
        "data": bar_labels,
        "axisLabel": {
            "color": theme.get("text_style", {}).get("color", "#c9d1d9"),
            "interval": 0,
            "fontSize": 11,
            "formatter": _WRAP_XAXIS_FN,
        },
    }
    opt["yAxis"] = {"type": "value", "show": False}
    opt["color"] = ["#8b3a3a", "#56d364"]
    opt["series"] = [
        {
            "name": "Before (god-class)",
            "type": "bar",
            "data": [
                {"value": v, "metric": m} for v, m in zip(before_vals, metrics)
            ],
            "label": {
                "show": True,
                "position": "top",
                "color": theme.get("text_style", {}).get("color", "#c9d1d9"),
                "formatter": _LABEL_FN,
            },
            "emphasis": {"focus": "series"},
        },
        {
            "name": "After (refactored)",
            "type": "bar",
            "data": [
                {"value": v, "metric": m} for v, m in zip(after_vals, metrics)
            ],
            "label": {
                "show": True,
                "position": "top",
                "color": theme.get("colors", {}).get("tech", "#56d364"),
                "formatter": _LABEL_FN,
            },
            "emphasis": {"focus": "series"},
        },
    ]
    return opt
```

Then add these 3 JS function string constants at module level (near the top of `echarts.py`, after the `TCFD_THEME_CONFIG` dict but before any `def build_` function). They must be Python string literals:

```python
# JS formatter source strings for build_pipeline_health_dashboard.
# Receives `params.data.metric` and returns a formatted string.
_LABEL_FN = (
    "function (params) {"
    "  var m = params.data && params.data.metric;"
    "  if (!m) return String(params.value);"
    "  var v = (m.unit === 'tests') ? Math.round(params.value) : params.value;"
    "  return v + ' ' + m.unit;"
    "}"
)

_PIPELINE_HEALTH_TOOLTIP_FN = (
    "function (params) {"
    "  return params.map(function (p) {"
    "    var m = p.data && p.data.metric;"
    "    if (!m) return p.seriesName + ': ' + p.value;"
    "    return p.seriesName + ' \u00b7 ' + p.name + '<br/>'"
    "      + '<b>' + p.value + ' ' + m.unit + '</b><br/>'"
    "      + '<span style=\"color:#8b949e;font-size:11px\">' + m.note + '</span>';"
    "  }).join('<hr/>');"
    "}"
)

_WRAP_XAXIS_FN = (
    "function (value) {"
    "  if (value.length <= 14) return value;"
    "  var words = value.split(' ');"
    "  var line = '', lines = [];"
    "  for (var i = 0; i < words.length; i++) {"
    "    if ((line + ' ' + words[i]).trim().length > 14) {"
    "      lines.push(line.trim()); line = words[i];"
    "    } else { line = line + ' ' + words[i]; }"
    "  }"
    "  if (line) lines.push(line.trim());"
    "  return lines.join('\\n');"
    "}"
)
```

Then update the test in Task 2.1: change `"formatter" in opt["tooltip"]` to `"formatter" in opt["tooltip"]` (already correct) and **add** an assertion that `opt["tooltip"]["formatter"] == _PIPELINE_HEALTH_TOOLTIP_FN` (or just verify it's a non-empty string).

- [ ] **Step 2.4: Run the new tests to verify they pass**

Run: `PYTHONPATH=src uv run pytest tests/test_visualization/test_echarts.py::TestPipelineHealthDashboard -v`
Expected: 8 passing tests.

- [ ] **Step 2.5: Run the full visualization test suite to check no regressions**

Run: `PYTHONPATH=src uv run pytest tests/test_visualization/ -v 2>&1 | tail -40`
Expected: `TestRefactorDashboard` is no longer collected (replaced by `TestPipelineHealthDashboard` in Step 2.1). 8 new dashboard tests pass; all other tests still pass.

If `TestRefactorDashboard` tests still exist in the file (you didn't replace them in Step 2.1), delete the entire class block (lines ~646-721).

- [ ] **Step 2.6: Commit**

```bash
git add src/tcfd_extractor/visualization/echarts.py tests/test_visualization/test_echarts.py
git commit -m "feat(echarts): Stage 5.2 — build_pipeline_health_dashboard replaces build_refactor_dashboard"
```

---

### Task 3: Replace Section 4 HTML/CSS/JS in `template.py`

**Files:**
- Modify: `src/tcfd_extractor/visualization/template.py:296-349` (Section 4 narrative)
- Modify: `src/tcfd_extractor/visualization/template.py:415-541` (JS init block + `bindDashboardClickHandler`)

- [ ] **Step 3.1: Locate the current Section 4 boundaries**

Run: `grep -n "4. Engineering excellence\|bindDashboardClickHandler\|__hrAppState\|x-data.*showGraph" src/tcfd_extractor/visualization/template.py`
Expected output (approximate line numbers):
```
296:      <h2>4. Engineering excellence</h2>
322:      <div x-data="{ showGraph: false }">
415:    window.__hrAppState = { showGraph: false };
509:    function bindDashboardClickHandler() {
540:      bindDashboardClickHandler();
```

- [ ] **Step 3.2: Replace Section 4 HTML block**

Open `template.py` at line 296. Replace the entire block from line 296 (`<section>` containing `<h2>4. Engineering excellence</h2>`) through line 349 (`</section>` closing tag) with the new HTML below.

Find the exact start by searching for: `<section>\n      <h2>4. Engineering excellence</h2>` (multi-line; use Edit with sufficient surrounding context to be unique).

Replace with:

```html
    <section class="engineering-excellence">
      <h2>4. Robust AI Pipeline Engineering</h2>
      <p class="subtitle">How we transformed a volatile LLM script into a
         fault-tolerant, industry-grade text processing mill.</p>

      <div class="engineering-layout-grid">
        <div id="echarts-pipeline-health-dashboard"
             class="echarts-chart"
             style="width:100%; height:380px; cursor: pointer;"
             @click="window.__hrToggleDeepDive && window.__hrToggleDeepDive()"></div>

        <div class="engineering-specs">
          <div class="spec-card">
            <h3>&#x1F6E1;&#xFE0F; Stochastic-to-Deterministic Defense</h3>
            <p>Deploying a local 35B model presents non-deterministic JSON
               deformations. We implemented a Pydantic-driven validation
               guardrail featuring a strict exception hierarchy
               (<code>LLMResponseParseError</code>) and automatic
               token-rate-limiting. Raw responses are safely isolated and logged
               without halting the entire multi-year batch run.</p>
          </div>
          <div class="spec-card">
            <h3>&#x26A1;&#xFE0F; Memory-Safe Streaming &amp; Concurrency</h3>
            <p>Processing 10,814 files sequentially triggers tight coupling and
               out-of-memory stalls. The refactored pipeline decouples
               orchestration into 8 single-responsibility submodules, shifting
               to a generator-based stream architecture. Controlled by a
               <code>ThreadPoolExecutor</code> semaphore, the pipeline achieved
               zero-leak concurrency across 25 years of financial reports.</p>
          </div>
          <div class="spec-card">
            <h3>&#x1F52C; Comprehensive Observability</h3>
            <p>To eliminate regressions caused by LLM prompt tuning, we expanded
               the test suite from 16 baseline specs to
               <strong>329+ automated tests</strong>. New evaluation submodules
               maintain a 95%&ndash;100% coverage rate, wrapping the entire AI
               infrastructure in a transparent, highly verifiable test harness.</p>
          </div>
        </div>
      </div>

      <div x-show="$store.pipelineUi.showDeepDive" x-transition.opacity.duration.300ms
           style="margin-top: 1rem;">
        <h3 style="margin-top: 1rem; color: var(--accent);">
          &#x1F9E9; Module Dependency Graph (click any bar to collapse)
        </h3>
        <p>Hover a module to highlight its import dependencies.</p>
        <div id="echarts-module-graph" class="echarts-chart"
             style="width:100%; height:480px;"></div>
      </div>
    </section>
```

- [ ] **Step 3.3: Add CSS rules to the `<style>` block**

Find the `<style>` block in `template.py`. Append these rules at the end (before `</style>`):

```css
      .engineering-layout-grid {
        display: grid;
        grid-template-columns: 1.4fr 1fr;
        gap: 1.5rem;
        align-items: start;
        margin-top: 1rem;
      }
      .engineering-specs {
        display: flex;
        flex-direction: column;
        gap: 1rem;
      }
      .spec-card {
        background: rgba(255, 255, 255, 0.02);
        border-left: 3px solid var(--accent, #56d364);
        border-radius: 4px;
        padding: 0.85rem 1rem;
      }
      .spec-card h3 {
        margin: 0 0 0.4rem 0;
        font-size: 1.05rem;
        color: var(--accent, #56d364);
      }
      .spec-card p {
        margin: 0;
        font-size: 0.9rem;
        line-height: 1.5;
        color: var(--text-muted, #8b949e);
      }
      @media (max-width: 900px) {
        .engineering-layout-grid { grid-template-columns: 1fr; }
      }
```

- [ ] **Step 3.4: Update the JS data injection and remove `window.__hrAppState`**

Find line 415 (`window.__hrAppState = { showGraph: false };`). Delete that single line.

Find line 421 (`refactorDashboard:  {{ refactor_dashboard_json|safe }},`). Replace with:
```javascript
      pipelineHealthDashboard:  {{ pipeline_health_dashboard_json|safe }},
```

- [ ] **Step 3.5: Replace `bindDashboardClickHandler` with `bindPipelineHealthClickHandler`**

Find the `bindDashboardClickHandler` function (lines 509-530) and its call from `DOMContentLoaded` (line 540). Replace the function definition AND the `bindDashboardClickHandler();` call.

Inside the `rebuildAllCharts()` function (or as a sibling, depending on layout), add:

```javascript
    function bindPipelineHealthClickHandler() {
      const el = document.getElementById('echarts-pipeline-health-dashboard');
      if (!el || !window.__hrCharts['echarts-pipeline-health-dashboard']) return;
      const chart = window.__hrCharts['echarts-pipeline-health-dashboard'];
      chart.on('click', function () { window.__hrToggleDeepDive(); });
    }
```

At the end of `rebuildAllCharts()`, add a call: `bindPipelineHealthClickHandler();`

Remove the entire `bindDashboardClickHandler()` function (lines 509-530 inclusive).

- [ ] **Step 3.6: Add Alpine store registration and `__hrToggleDeepDive` function**

Find the page-init `<script>` block. Inside `document.addEventListener('DOMContentLoaded', ...)` (or as a separate `alpine:init` listener), add:

```javascript
    // Alpine.js: pipelineUi store — controls the hidden Module Dependency Graph
    document.addEventListener('alpine:init', function() {
      if (window.Alpine) Alpine.store('pipelineUi', { showDeepDive: false });
    });

    // Toggle the hidden Module Dependency Graph on any bar click.
    window.__hrToggleDeepDive = function () {
      if (!window.Alpine) return;
      const s = Alpine.store('pipelineUi');
      s.showDeepDive = !s.showDeepDive;
      if (s.showDeepDive) {
        Alpine.nextTick(function () {
          const el = document.getElementById('echarts-module-graph');
          if (el && window.echarts) {
            const inst = echarts.getInstanceByDom(el);
            if (inst) inst.resize();   // prevent 0x0 hidden canvas
          }
        });
      }
    };
```

- [ ] **Step 3.7: Verify no dead references remain**

Run: `grep -n "bindDashboardClickHandler\|__hrAppState\|refactor_dashboard_json\|refactorDashboard\|echarts-refactor-dashboard" src/tcfd_extractor/visualization/template.py`
Expected: 0 matches.

- [ ] **Step 3.8: Verify the template module still parses**

The full HTML render needs the new `html_assembler.py` wiring (Chunk 2, Task 4) and `build_report.py` updates (Chunk 2, Task 5) before it can succeed end-to-end. For Chunk 1, only verify the template module imports cleanly:

Run: `PYTHONPATH=src uv run python -c "import tcfd_extractor.visualization.template; print('TEMPLATE imported OK')"`
Expected: `TEMPLATE imported OK`.

- [ ] **Step 3.9: Commit**

```bash
git add src/tcfd_extractor/visualization/template.py
git commit -m "feat(template): Stage 5.3 — Section 4 narrative + Alpine pipelineUi store + new click handler"
```

---

## Chunk 2: Wire new dashboard into html_assembler, remove old static chart, update build script, end-to-end verification

**Prerequisite**: Chunk 2 depends on Chunk 1's commits (Tasks 1, 2, 3). Specifically:
- Task 1 must commit `pipeline_metrics.py` (provides `ALL_STATIC_METRICS`, `TEST_COVERAGE_TEMPLATE`, `PipelineMetric`).
- Task 2 must commit `build_pipeline_health_dashboard` (imported by Task 4) and replace `build_refactor_dashboard` (so Task 4's import doesn't break).
- Task 3 must update `template.py` so the `pipeline_health_dashboard_json` template variable exists.

If you run Chunk 2 standalone, the html_assembler test in Step 4.5 will fail with `jinja2.UndefinedError` (template expects `pipeline_health_dashboard_json` but it isn't passed) or `ImportError` (the old `build_refactor_dashboard` is gone but `html_assembler.py` still imports it).

**Execute Chunk 1 first, verify it passes, then proceed to Chunk 2.**

### Task 4: Update `html_assembler.py` — drop `refactor_bar_b64` + `_build_refactor_dashboard_data`, accept metrics kwarg, render new dashboard

**Files:**
- Modify: `src/tcfd_extractor/visualization/html_assembler.py:21,86-146,149-227`
- Modify: `tests/test_visualization/test_html_assembler.py` (multiple sites — see Step 4.4)

- [ ] **Step 4.1: Locate exact line numbers**

Run: `grep -n "build_refactor_dashboard\|_build_refactor_dashboard_data\|refactor_bar_b64\|refactor_dashboard_json\|refactor_b64" src/tcfd_extractor/visualization/html_assembler.py`
Expected output (approximate):
```
21:    build_refactor_dashboard,
86:def _build_refactor_dashboard_data(refactor_stats: dict) -> dict:
146:    return {"metrics": metrics}
152:    refactor_bar_b64: str = "",
187:    dashboard_opt = build_refactor_dashboard(dashboard_data, TCFD_THEME_CONFIG)
217:        refactor_dashboard_json=dashboard_json,
220:        refactor_b64=refactor_bar_b64,
```

- [ ] **Step 4.2: Update the `echarts` imports**

In `html_assembler.py` line 21, replace:
```python
    build_refactor_dashboard,
```
with:
```python
    build_pipeline_health_dashboard,
```

- [ ] **Step 4.3: Delete `_build_refactor_dashboard_data` function and refactor `assemble_html`**

In `html_assembler.py`, **delete the entire `_build_refactor_dashboard_data` function** (lines 86-146 inclusive). Replace it with **nothing** (just remove the block).

Then update the `assemble_html` function (starting at line 149):

Replace the **signature**:
```python
def assemble_html(
    results_root: Path,
    *,
    refactor_bar_b64: str = "",
    module_graph_svg: str = "",
    refactor_stats: dict | None = None,
    build_date: str | None = None,
) -> str:
```
with:
```python
def assemble_html(
    results_root: Path,
    *,
    pipeline_metrics: list | None = None,
    module_graph_svg: str = "",
    refactor_stats: dict | None = None,
    build_date: str | None = None,
) -> str:
```

Replace the **docstring** (lines 157-164) with:
```python
    """Load data, build charts, render template. Returns final HTML string.

    Stage 2: 注入 __hrTranslateMap (全量 KEYWORD_TRANSLATIONS) 和
    __hrContextIndex (节点 + sankey 边 → context 列表, 限 3 sample)。

    Stage 5: 新增 pipeline_health_dashboard + module_graph 两个 ECharts option,
    取代静态 PNG 和旧 refactor_dashboard。`pipeline_metrics` 是 4 个
    PipelineMetric 实例的列表; 若为 None 则用静态默认 (MEMORY_FOOTPRINT,
    CONCURRENCY, SCHEMA_COMPLIANCE + 用 refactor_stats 拼出的 Test Coverage)。
    """
```

Replace the **dashboard construction block** (lines 184-187):
```python
    # Stage 5: 构建 Software Health Dashboard (取代静态 PNG)
    refactor_stats = refactor_stats or {}
    dashboard_data = _build_refactor_dashboard_data(refactor_stats)
    dashboard_opt = build_refactor_dashboard(dashboard_data, TCFD_THEME_CONFIG)
```
with:
```python
    # Stage 5: 构建 AI Pipeline Health Dashboard (取代静态 PNG + 旧 refactor dashboard)
    from tcfd_extractor.visualization.pipeline_metrics import (
        ALL_STATIC_METRICS, TEST_COVERAGE_TEMPLATE, PipelineMetric,
    )
    refactor_stats = refactor_stats or {}
    if pipeline_metrics is None:
        # 默认: 3 个静态指标 + 1 个从 refactor_stats.test_before/after 构造的 Test Coverage
        test_coverage = PipelineMetric(
            name=TEST_COVERAGE_TEMPLATE.name,
            unit=TEST_COVERAGE_TEMPLATE.unit,
            before=refactor_stats.get("test_before", 16),
            after=refactor_stats.get("test_after", 0) or 0,
            note=TEST_COVERAGE_TEMPLATE.note,
        )
        pipeline_metrics = [*ALL_STATIC_METRICS, test_coverage]
    dashboard_opt = build_pipeline_health_dashboard(pipeline_metrics, TCFD_THEME_CONFIG)
```

Replace the **`return HTML_TEMPLATE.render(...)` block** (lines 211-227):
```python
    return HTML_TEMPLATE.render(
        sunburst_json=sunburst_json,
        streamgraph_json=streamgraph_json,
        network_json=network_json,
        sankey_json=sankey_json,
        # Stage 5: 新增
        refactor_dashboard_json=dashboard_json,
        module_graph_json=module_graph_json,
        # Stage 5: 兼容旧字段 (template 已不再使用, 但保留以防外部依赖)
        refactor_b64=refactor_bar_b64,
        module_graph_svg=module_graph_svg,
        refactor_stats=refactor_stats,
        build_date=build_date or date.today().isoformat(),
        # Stage 2 注入
        translate_map_json=translate_map_json,
        context_index_json=context_index_json,
    )
```
with:
```python
    return HTML_TEMPLATE.render(
        sunburst_json=sunburst_json,
        streamgraph_json=streamgraph_json,
        network_json=network_json,
        sankey_json=sankey_json,
        # Stage 5: 新增
        pipeline_health_dashboard_json=dashboard_json,
        module_graph_json=module_graph_json,
        module_graph_svg=module_graph_svg,
        refactor_stats=refactor_stats,
        build_date=build_date or date.today().isoformat(),
        # Stage 2 注入
        translate_map_json=translate_map_json,
        context_index_json=context_index_json,
    )
```

(Note: `refactor_bar_b64` and `refactor_dashboard_json` are removed; `pipeline_health_dashboard_json` is the new template variable matching `template.py` Step 3.4. `module_graph_svg` is kept as an unused kwarg for backward compatibility with `build_report.py` even though the template no longer references it — see Task 5.)

- [ ] **Step 4.4: Update `tests/test_visualization/test_html_assembler.py`**

This file has 14 occurrences of `refactor_bar_b64` plus other affected assertions. The cleanest fix is a series of `sed` edits + a manual import cleanup:

**Pre-step**: Remove the `build_refactor_bar` import (lines 6-9):

```python
# Replace the multi-line import block:
from tcfd_extractor.visualization.static_charts import (
    build_module_graph_svg,
    build_refactor_bar,
)
# with just:
from tcfd_extractor.visualization.static_charts import build_module_graph_svg
```

(Without this, Task 5 will leave a dangling import and break the file.)

**Then run the sed edits**:

Run: `sed -i 's/refactor_bar_b64=build_refactor_bar([^)]*)//g' tests/test_visualization/test_html_assembler.py`
Expected: removes the kwarg from every `assemble_html(...)` call.

Run: `sed -i 's/build_refactor_bar([^)]*)//g' tests/test_visualization/test_html_assembler.py`
Expected: removes any orphan `build_refactor_bar(...)` invocations left over after the first sed.

Run: `sed -i 's/, refactor_bar_b64="[^"]*"//g; s/refactor_bar_b64="[^"]*"//g' tests/test_visualization/test_html_assembler.py`
Expected: removes any string-form `refactor_bar_b64=` kwargs (zero matches expected).

Run: `grep -n "refactor_bar_b64\|build_refactor_bar\|build_refactor_dashboard\|refactor_dashboard_json" tests/test_visualization/test_html_assembler.py`
Expected: 0 matches.

Run: `grep -n '"Engineering excellence"\|"x-data"\|showGraph' tests/test_visualization/test_html_assembler.py`
Expected: a few hits — the assertions need updating:

- Line 71 (verify by reading): replace `"Engineering excellence" in html` with `"Robust AI Pipeline Engineering" in html`.
- Line 130 area: remove the assertion `"x-data" in html and "showGraph" in html` (the `x-data` wrapper is gone).
- Line 134-156 (`test_refactor_chart_inlined`): rename to `test_pipeline_health_chart_inlined`. Update the assertion strings to match the new Section 4 HTML: assert `"echarts-pipeline-health-dashboard"` in html, `"Stochastic-to-Deterministic Defense"` in html, `"Memory-Safe Streaming"` in html, `"Comprehensive Observability"` in html, `"pipelineHealthDashboard"` in html.

- [ ] **Step 4.5: Run the html_assembler tests**

Run: `PYTHONPATH=src uv run pytest tests/test_visualization/test_html_assembler.py -v 2>&1 | tail -30`
Expected: all tests pass.

If any test fails:
- If `KeyError: 'refactor_bar_b64'` or `TypeError: assemble_html() got an unexpected keyword argument 'refactor_bar_b64'` → re-run the `sed` commands from Step 4.4.
- If `assert "Robust AI Pipeline Engineering" in html` fails → confirm `template.py` Step 3.2 was applied (the new Section 4 `<h2>` should be there).
- If `assert "pipelineHealthDashboard" in html` fails → confirm `template.py` Step 3.4 was applied (the new `__hrOpts` entry should be there).

- [ ] **Step 4.6: Commit**

```bash
git add src/tcfd_extractor/visualization/html_assembler.py tests/test_visualization/test_html_assembler.py
git commit -m "feat(assembler): Stage 5.4 — drop refactor_bar_b64 + _build_refactor_dashboard_data; accept pipeline_metrics kwarg"
```

---

### Task 5: Remove `build_refactor_bar` from `static_charts.py` and its tests

**Files:**
- Modify: `src/tcfd_extractor/visualization/static_charts.py:16-62` (delete function)
- Modify: `tests/test_visualization/test_static_charts.py:8-29` (delete test class)

- [ ] **Step 5.1: Delete `build_refactor_bar` function**

Open `src/tcfd_extractor/visualization/static_charts.py`. Delete the entire `build_refactor_bar(...)` function (lines 16-62 inclusive). The remaining function `build_module_graph_svg` (lines 65+) stays unchanged.

- [ ] **Step 5.2: Drop the now-unused `base64` import**

`build_refactor_bar` was the only consumer of `import base64` at line 4 of `static_charts.py`. After deleting it, `base64` becomes dead code. Remove that single import line (keep `import io` — it's still used by `build_module_graph_svg` for the `BytesIO` buffer).

- [ ] **Step 5.3: Delete `TestBuildRefactorBar` test class**

Open `tests/test_visualization/test_static_charts.py`. Delete the entire `TestBuildRefactorBar` class (lines 8-29 inclusive, including the `build_refactor_bar` import). The `TestModuleGraphSvg` class stays unchanged.

- [ ] **Step 5.4: Run the static_charts tests**

Run: `PYTHONPATH=src uv run pytest tests/test_visualization/test_static_charts.py -v`
Expected: only `TestModuleGraphSvg` tests run; all pass.

- [ ] **Step 5.5: Commit**

```bash
git add src/tcfd_extractor/visualization/static_charts.py tests/test_visualization/test_static_charts.py
git commit -m "refactor(static_charts): Stage 5.5 — drop build_refactor_bar (replaced by ECharts dashboard)"
```

---

### Task 6: Update `scripts/build_report.py` — remove old plumbing, pass new metrics kwarg

**Files:**
- Modify: `scripts/build_report.py:27-65, 109-160`

- [ ] **Step 6.1: Locate the god-class metric helpers**

Run: `grep -n "get_git_lines_before\|get_current_lines\|get_module_stats\|get_test_count_before\|build_refactor_bar\|refactor_b64\|build_refactor_dashboard\|refactor_stats" scripts/build_report.py`
Expected output:
```
27:def get_git_lines_before(path: Path) -> int:
41:def get_current_lines(path: Path) -> int:
49:def get_module_stats() -> tuple[int, int, int]:
68:def get_test_count_before() -> int:
109:    god_class_path = Path("src/tcfd_extractor/evaluation/cooccurrence_evaluator.py")
110:    god_class_lines_before = get_git_lines_before(god_class_path)
117:    god_class_lines_after = get_current_lines(god_class_path)
118:    total_module_lines, module_count, test_count_after = get_module_stats()
130:    from tcfd_extractor.visualization.static_charts import build_refactor_bar
131:    refactor_b64 = build_refactor_bar(
148:    from tcfd_extractor.visualization.html_assembler import assemble_html
149:    html = assemble_html(
```

- [ ] **Step 6.2: Replace the metric-gathering and chart-building block**

In `build_report.py`, **delete the entire `get_git_lines_before` function** (lines 27-38 inclusive). **Keep** `get_test_count_before` (lines 68-82) because it still works for the new dashboard.

**Delete the entire `get_current_lines` function** (lines 41-46 inclusive).

**Delete the entire `get_module_stats` function** (lines 49-65 inclusive).

Replace the body inside `main()` from line 109 through line 138 (everything that uses the removed helpers) with:

```python
    # Compute test counts (kept; old god-class metric helpers removed).
    test_count_before = get_test_count_before()
    test_count_after = _run_pytest_collect()

    if test_count_after < 50:
        print(
            f"WARNING: pytest collection returned only {test_count_after} tests. "
            f"Expected ~200+. Check that tests/ exists and pytest is installed.",
            file=sys.stderr,
        )

    # Stage 5: 构建 4 个 PipelineMetric (3 静态 + 1 动态 Test Coverage)
    from tcfd_extractor.visualization.pipeline_metrics import (
        ALL_STATIC_METRICS, TEST_COVERAGE_TEMPLATE, PipelineMetric,
    )
    test_coverage = PipelineMetric(
        name=TEST_COVERAGE_TEMPLATE.name,
        unit=TEST_COVERAGE_TEMPLATE.unit,
        before=test_count_before,
        after=test_count_after,
        note=TEST_COVERAGE_TEMPLATE.note,
    )
    pipeline_metrics = [*ALL_STATIC_METRICS, test_coverage]
```

- [ ] **Step 6.3: Add a `_run_pytest_collect()` helper**

Add a new helper function above `main()` (insert right after `get_test_count_before`):

```python
def _run_pytest_collect() -> int:
    """Run `pytest --collect-only -q` and return the test count.

    Tries `pytest` directly first (fast path when already inside a uv env),
    then falls back to `uv run pytest` if the bare command isn't on PATH.
    Returns 0 on failure (the build proceeds; the warning in main() covers it).
    """
    # Stable substring across pytest 7/8/9: "X tests collected"
    for cmd in (["pytest", "--collect-only", "-q", "tests/"],
                ["uv", "run", "pytest", "--collect-only", "-q", "tests/"]):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            for line in result.stdout.splitlines() + result.stderr.splitlines():
                if "tests collected" in line:
                    return int(line.split()[0])
        except Exception:
            continue
    return 0
```

- [ ] **Step 6.4: Replace the `assemble_html` call**

Replace the `assemble_html(...)` invocation (lines 148-160) with:

```python
    print("Assembling HTML...")
    from tcfd_extractor.visualization.html_assembler import assemble_html
    html = assemble_html(
        results_root=Path("output/evaluate_cooccurrence"),
        pipeline_metrics=pipeline_metrics,
        module_graph_svg=module_svg,
        refactor_stats={
            "test_before": test_count_before,
            "test_after": test_count_after,
        },
    )
```

- [ ] **Step 6.5: Run the build script (smoke test)**

Run: `python scripts/build_report.py --output /tmp/report_test/ 2>&1 | tail -20`
Expected: build succeeds, prints "✅ Build complete. Report at: /tmp/report_test/index.html".

If the script fails:
- If `ModuleNotFoundError: No module named 'tcfd_extractor.visualization.pipeline_metrics'` → Task 1 didn't commit; re-run `git log --oneline -5` and verify.
- If `KeyError: 'refactor_bar_b64'` in some old call site → re-grep for `refactor_bar_b64` across `scripts/` and `tests/`; only `build_report.py` should have it (now removed in this Task).
- If `BUILD FAILED: leakage check returned non-zero` → the new copy leaked a real company name; inspect `index.html` and remove the offending string.

- [ ] **Step 6.6: Verify the rendered HTML contains the new Section 4**

Run: `grep -c "AI Pipeline Resilience & Engineering Health\|Stochastic-to-Deterministic Defense\|Memory-Safe Streaming\|Comprehensive Observability" /tmp/report_test/index.html`
Expected: 4 (one match per string).

Run: `grep -c "pipelineHealthDashboard\|echarts-pipeline-health-dashboard\|__hrToggleDeepDive" /tmp/report_test/index.html`
Expected: ≥ 3.

- [ ] **Step 6.7: Commit**

```bash
git add scripts/build_report.py
git commit -m "feat(build): Stage 5.6 — pass pipeline_metrics to assemble_html; remove god-class metric helpers"
```

---

### Task 7: Final cleanup grep + full test suite + commit any leftovers

**Files:**
- Modify: any file that still references removed names

- [ ] **Step 7.1: Verify no dead references remain anywhere**

Run: `rg "refactor_dashboard|refactor-bar|build_refactor_bar|TestRefactorDashboard|TestBuildRefactorBar|__hrAppState|bindDashboardClickHandler|_build_refactor_dashboard_data" src/ tests/ scripts/`
Expected: 0 matches.

If any match found, delete it (most likely a stale test assertion or a leftover import).

- [ ] **Step 7.2: Run the full visualization test suite**

Run: `PYTHONPATH=src uv run pytest tests/test_visualization/ -v 2>&1 | tail -20`
Expected: all tests pass; total count ≥ 184 (baseline 177 + 5 new metrics + 8 new dashboard − 4 old dashboard − 2 old bar = +7 net).

- [ ] **Step 7.3: Run the full project test suite (excluding known-broken modules)**

Run: `PYTHONPATH=src uv run pytest tests/ -v --ignore=tests/test_annual_report_cleaner.py --ignore=tests/test_clustering/test_clustering.py --ignore=tests/test_clustering/test_ingestion.py 2>&1 | tail -10`
Expected: ≥ 329 passing tests (matches the Section 4 "329+" KPI). The `test_ingestion.py` ignore is needed because of a `libcudnn.so.9` collection error unrelated to this work.

- [ ] **Step 7.4: Final end-to-end build**

Run: `rm -rf /tmp/report_final && python scripts/build_report.py --output /tmp/report_final/ --target github-pages 2>&1 | tail -5`
Expected: `✅ Build complete. Report at: /tmp/report_final/index.html`.

(The `--target github-pages` flag is explicit to match the production deploy: the report loads ECharts + Alpine + Mermaid via CDN, identical to what GitHub Pages will serve. Using `--target email-attachment` would change the visual behavior since that target inlines the JS.)

- [ ] **Step 7.5: Spot-check the new Section 4 visually**

Open `/tmp/report_final/index.html` in a browser:
- Scroll to "4. Robust AI Pipeline Engineering"
- Confirm: chart title "AI Pipeline Resilience & Engineering Health", 4 metric groups on X-axis, 2 bars per group (red Before, green After)
- Click any bar → module graph appears below
- Click any bar again → module graph collapses
- Resize the browser window below 900px → layout collapses to 1 column

If any of these fail, debug per the spec's §10 DoD manual-test instructions. Record results in `output/report/BUILD_LOG.md` under "Section 4 manual test".

- [ ] **Step 7.6: Stage the regenerated `output/report/` artifacts**

Run: `git add output/report/index.html output/report/README.md output/report/.nojekyll output/report/BUILD_LOG.md`
Expected: files are tracked. (If `.gitignore` excludes them, force-add with `git add -f`.)

- [ ] **Step 7.7: Final commit**

```bash
git commit -m "feat(hr-report): Stage 5.7 — regenerated output with AI Pipeline Resilience Section 4"
```

---

## Summary

- **7 tasks** across 2 chunks.
- **Net new tests**: +13 (5 metrics + 8 dashboard).
- **Net removed tests**: −6 (4 old dashboard + 2 old bar).
- **Files created**: 2 (`pipeline_metrics.py`, `test_pipeline_metrics.py`).
- **Files modified**: 8 (`echarts.py`, `template.py`, `html_assembler.py`, `static_charts.py`, `build_report.py`, `test_echarts.py`, `test_html_assembler.py`, `test_static_charts.py`).
- **Commits**: 7 (one per task), plus 1 final regeneration commit = **8 commits total**.
- **Estimated effort**: ~3-4 hours for a focused engineer following TDD.