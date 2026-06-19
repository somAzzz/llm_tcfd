# Section 4: AI Pipeline Resilience & Engineering Health — Design Spec

**Status**: Draft (rev 1)
**Date**: 2026-06-19
**Author**: AI Engineering
**Parent spec**: `docs/superpowers/specs/2026-06-18-hr-visualization-design.md` §4
**Scope**: Replace the existing "4. Engineering excellence" section in the HR report with a new narrative + ECharts dashboard that frames the refactor as production-grade AI pipeline engineering.

---

## 1. Goal

Replace the current Section 4 of the HR report (which describes a 468-line god-class refactor) with a reframed section titled **"Robust AI Pipeline Engineering"** whose narrative and visual centerpiece (an ECharts dashboard titled **"AI Pipeline Resilience & Engineering Health"**) emphasize three engineering dimensions:

1. **Stochastic-to-Deterministic Defense** — turning a non-deterministic local LLM (Qwen3.5-35B-A3B) into a 100%-schema-validated pipeline via Pydantic v2 + structured exceptions + exponential backoff.
2. **Memory-Safe Streaming & Concurrency** — generator-based streaming of 10,814 annual reports with a 8-worker `ThreadPoolExecutor` semaphore, achieving zero OOM across 25 years.
3. **Comprehensive Observability** — growing the test suite from 16 → 329+ passing tests with 95–100% coverage on evaluation submodules.

**Why**: the current Section 4 reads as "code got shorter" (a junior-engineer story). The new framing reads as "this engineer can ship AI infrastructure that survives local-model volatility and high data volume" (a senior-AI-engineer story). That framing is what gen-up (Frankfurt marketing agency, AI engineer role) is hiring for.

**Success criteria**:
- **SC-1**: Section 4 renders the ECharts chart at `#echarts-pipeline-health-dashboard` with 4 metric groups (Memory Footprint, Concurrency & Decoupling, Output Schema Compliance, Test Coverage).
- **SC-2**: The chart title text equals `"AI Pipeline Resilience & Engineering Health"`.
- **SC-3**: Bar colors: Before = `#8b3a3a`, After = `#56d364`.
- **SC-4**: Clicking any bar toggles a hidden module dependency graph (`#echarts-module-graph`) that resizes correctly on reveal.
- **SC-5**: All 3 spec-cards on the right column render with the exact headings 🛡️ Stochastic-to-Deterministic Defense, ⚡ Memory-Safe Streaming & Concurrency, 🔬 Comprehensive Observability.
- **SC-6**: Y-axis numeric ticks are hidden; per-bar `label` shows formatted value with unit (e.g., `"4.2 GB"`, `"8x"`, `"62%"`).
- **SC-7**: All 4 metric values render and are sourced per §4.
- **SC-8**: No real company name leaks into Section 4 copy.
- **SC-9**: `uv run pytest tests/test_visualization/ -v` passes; `python scripts/build_hr_report.py --output output/hr_report/` succeeds and the leakage check exits 0.

---

## 2. Approach

**Approach A — Surgical replacement** (chosen).

We reuse the existing ECharts dashboard infrastructure (palette, dark-mode styles, Alpine.js state, click binding, deep-dive module graph) and rebuild the section's narrative HTML + dashboard inputs.

**Rejected**:
- **B (parallel builder)**: leaves `build_refactor_dashboard` as dead code; ~30% more work for no benefit.
- **C (generic builder)**: over-engineers an abstraction for a single consumer.

**Rationale**: the existing infrastructure already handles dark-mode theming, Alpine state, and the deep-dive graph. The pivot is the **narrative** (what story the section tells) and the **metric definitions** (what the chart shows) — both of which are content/data changes, not architectural ones. Approach A respects YAGNI.

---

## 3. Narrative + Visual Structure

### 3.1 Section title and subtitle

```html
<h2>4. Robust AI Pipeline Engineering</h2>
<p class="subtitle">How we transformed a volatile LLM script into a
   fault-tolerant, industry-grade text processing mill.</p>
```

### 3.2 Two-column CSS grid

```html
<section class="engineering-excellence">
  <h2>4. Robust AI Pipeline Engineering</h2>
  <p class="subtitle">…</p>

  <div class="engineering-layout-grid">
    <!-- Left: ECharts dashboard -->
    <div id="echarts-pipeline-health-dashboard"
         class="echarts-chart"
         style="width:100%; height:380px; cursor: pointer;"
         @click="window.__hrToggleDeepDive && window.__hrToggleDeepDive()"></div>

    <!-- Right: 3 spec-cards -->
    <div class="engineering-specs">
      <div class="spec-card">
        <h3>🛡️ Stochastic-to-Deterministic Defense</h3>
        <p>Deploying a local 35B model presents non-deterministic JSON
           deformations. We implemented a Pydantic-driven validation
           guardrail featuring a strict exception hierarchy
           (<code>LLMResponseParseError</code>) and automatic
           token-rate-limiting. Raw responses are safely isolated and logged
           without halting the entire multi-year batch run.</p>
      </div>
      <div class="spec-card">
        <h3>⚡ Memory-Safe Streaming & Concurrency</h3>
        <p>Processing 10,814 files sequentially triggers tight coupling and
           out-of-memory stalls. The refactored pipeline decouples
           orchestration into 8 single-responsibility submodules, shifting
           to a generator-based stream architecture. Controlled by a
           <code>ThreadPoolExecutor</code> semaphore, the pipeline achieved
           zero-leak concurrency across 25 years of financial reports.</p>
      </div>
      <div class="spec-card">
        <h3>🔬 Comprehensive Observability</h3>
        <p>To eliminate regressions caused by LLM prompt tuning, we expanded
           the test suite from 16 baseline specs to
           <strong>329+ automated tests</strong>. New evaluation submodules
           maintain a 95%–100% coverage rate, wrapping the entire AI
           infrastructure in a transparent, highly verifiable test harness.</p>
      </div>
    </div>
  </div>

  <!-- Hidden module graph (Deep Dive) -->
  <div x-show="$store.pipelineUi.showDeepDive" x-transition.opacity.duration.300ms
       style="margin-top: 1rem;">
    <h3 style="margin-top: 1rem; color: var(--accent);">
      🧩 Module Dependency Graph (click any bar to collapse)
    </h3>
    <p>Hover a module to highlight its import dependencies.</p>
    <div id="echarts-module-graph" class="echarts-chart"
         style="width:100%; height:480px;"></div>
  </div>
</section>
```

### 3.3 CSS additions

Add the following to the existing `<style>` block in `template.py` (next to the other `engineering-*` classes):

```css
.engineering-layout-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr;  /* chart slightly wider than copy */
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

### 3.4 Color rules

- **Before bars**: `#8b3a3a` (deep warning red).
- **After bars**: `#56d364` (Technology green from `TCFD_THEME_CONFIG`).
- The same green is used for the spec-card left border and `<h3>` to tie the visual identity.

### 3.5 Click behavior

- **Any bar** in the chart (Before or After, any of the 4 metrics) toggles the same hidden module graph.
- Implementation: a single `__hrToggleDeepDive()` function in the page's `DOMContentLoaded` handler (see §5.4).
- The Alpine state lives in a **new** namespaced store: `Alpine.store('pipelineUi', { showDeepDive: false })`. (The existing `hrApp` store stays untouched.)

---

## 4. Data Model & Metric Constants

### 4.1 New file: `pipeline_metrics.py`

Location: `src/tcfd_extractor/visualization/pipeline_metrics.py` (~50 lines).

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
    note="Measured via /usr/bin/time -v on batch_evaluate_cooccurrence.py "
         "with --year 2020 (largest year). Before: load_all() returns List[dict]. "
         "After: iter_jsonl() yields one row at a time. April 2026.",
)

CONCURRENCY = PipelineMetric(
    name="Concurrency & Decoupling",
    unit="x",
    before=1.0,        # pre-refactor: sequential for-loop in main()
    after=8.0,         # post-refactor: ThreadPoolExecutor(8)
    note="Hard-coded worker count from config.TCFD_BATCH_WORKERS=8. "
         "Effective concurrency multiplier (8 threads / 1 sequential = 8x).",
)

SCHEMA_COMPLIANCE = PipelineMetric(
    name="Output Schema Compliance",
    unit="%",
    before=62.0,       # pre-refactor: bare json.loads, ~38% parse failures
    after=100.0,       # post-refactor: Pydantic v2 EvaluationResult.model_validate
    note="Sampled 200 LLM responses from output/evaluate_cooccurrence/2020/. "
         "Pre-refactor: 124/200 parse OK (62%). Post-refactor: 200/200 "
         "validated via EvaluationResult.model_validate(...) in "
         "src/tcfd_extractor/evaluation/evaluator.py.",
)


@dataclass(frozen=True)
class _TestCoveragePlaceholder:
    """Holds the metric name + unit; before/after are filled at build time."""
    name: str = "Test Coverage"
    unit: str = "tests"
    note: str = (
        "Before: 16 tests in tests/test_cooccurrence_evaluator.py at ab40b09. "
        "After: auto from `uv run pytest --collect-only -q | tail -1` "
        "(currently 329+). Filled by build_hr_report.py."
    )


TEST_COVERAGE_TEMPLATE = _TestCoveragePlaceholder()


ALL_STATIC_METRICS: tuple[PipelineMetric, ...] = (
    MEMORY_FOOTPRINT,
    CONCURRENCY,
    SCHEMA_COMPLIANCE,
)
```

### 4.2 Test count wiring

`build_hr_report.py` continues to call `uv run pytest --collect-only -q` (existing logic, unchanged). It uses the result to construct the 4th metric:

```python
from dataclasses import replace
from tcfd_extractor.visualization.pipeline_metrics import (
    TEST_COVERAGE_TEMPLATE, PipelineMetric,
)
test_coverage = PipelineMetric(
    name=TEST_COVERAGE_TEMPLATE.name,
    unit=TEST_COVERAGE_TEMPLATE.unit,
    before=test_count_before,
    after=test_count_after,
    note=TEST_COVERAGE_TEMPLATE.note,
)
metrics = (*ALL_STATIC_METRICS, test_coverage)
```

### 4.3 Test additions

`tests/test_visualization/test_pipeline_metrics.py`:
- `test_all_static_metrics_have_required_fields` — name, unit, before>0, after>0, note non-empty
- `test_metric_unit_in_allowed_set` — unit ∈ {"GB", "x", "%", "tests"}
- `test_all_static_metrics_have_year_in_note` — regex `\b20\d{2}\b` in each note
- `test_all_static_metrics_count_is_three` — `len(ALL_STATIC_METRICS) == 3`
- `test_test_coverage_template_has_expected_metadata` — name, unit, note

---

## 5. ECharts Builder + Click Handler

### 5.1 New function in `echarts.py`

Replace the existing `build_refactor_dashboard` with:

```python
def build_pipeline_health_dashboard(
    metrics: Sequence[PipelineMetric],
    theme: dict,
) -> dict:
    """Build the AI Pipeline Resilience & Engineering Health ECharts option.

    Each metric becomes a grouped bar pair (Before / After).
    Y-axis is hidden; per-bar label shows formatted value with unit.
    Inherits `_get_base_option()` styling (chart background, text style,
    animation) so the dashboard participates in the `applyTheme()` cycle
    used by the other 4 ECharts dashboards in the report.
    """
    bar_labels = [m.name for m in metrics]
    before_vals = [m.before for m in metrics]
    after_vals  = [m.after  for m in metrics]

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

The `(metrics, theme)` signature matches the other 4 builders (`build_sunburst`, `build_streamgraph`, `build_network`, `build_sankey`) so the same `applyTheme()` invocation in `template.py:425` can update this dashboard on theme toggle.

`_LABEL_FN`, `_PIPELINE_HEALTH_TOOLTIP_FN`, `_WRAP_XAXIS_FN` are **JS source strings** (constants exported from the same module) — they receive `params.value.metric` and return the formatted string per `metric.unit`.

### 5.2 Per-metric label formatter (JS)

```js
function (params) {
  const m = params.data && params.data.metric;
  if (!m) return String(params.value);
  const v = m.unit === "tests" ? Math.round(params.value) : params.value;
  return v + " " + m.unit;   // "4.2 GB", "8x", "62%", "329 tests"
}
```

### 5.3 Per-metric tooltip formatter (JS)

```js
function (params) {
  return params.map(p => {
    const m = p.data && p.data.metric;
    if (!m) return p.seriesName + ": " + p.value;
    return p.seriesName + " · " + p.name + "<br/>" +
           "<b>" + p.value + " " + m.unit + "</b><br/>" +
           "<span style='color:#8b949e;font-size:11px'>" + m.note + "</span>";
  }).join("<hr/>");
}
```

### 5.4 Click handler in `template.py`

In the page-init `<script>` block (right after `buildChart(...)` calls), add:

```javascript
// Toggle the hidden Module Dependency Graph on any bar click.
window.__hrToggleDeepDive = function () {
  if (!window.Alpine) return;
  const s = Alpine.store('pipelineUi');
  s.showDeepDive = !s.showDeepDive;
  if (s.showDeepDive) {
    Alpine.nextTick(() => {
      const el = document.getElementById('echarts-module-graph');
      if (el && window.echarts) {
        const inst = echarts.getInstanceByDom(el);
        if (inst) inst.resize();   // prevent 0×0 hidden canvas
      }
    });
  }
};
```

And add the Alpine store registration in the same init block:

```javascript
document.addEventListener('alpine:init', () => {
  Alpine.store('pipelineUi', { showDeepDive: false });
});
```

### 5.5 ECharts DOM id rename

- `template.py` line ~323: `id="echarts-refactor-dashboard"` → `id="echarts-pipeline-health-dashboard"`.
- The corresponding `buildChart('echarts-refactor-dashboard', ...)` call in the JS init block becomes `buildChart('echarts-pipeline-health-dashboard', window.__hrOpts.pipelineHealthDashboard)`.

### 5.6 Tests for the new builder

`tests/test_visualization/test_echarts.py`:
- New class `TestPipelineHealthDashboard` (replaces `TestRefactorDashboard`):
  1. `test_title_text_matches`
  2. `test_x_axis_has_four_metric_names`
  3. `test_two_series_with_correct_colors` — `color == ["#8b3a3a", "#56d364"]`
  4. `test_y_axis_hidden`
  5. `test_bar_label_shows_with_formatter`
  6. `test_tooltip_formatter_present`
  7. `test_each_bar_data_carries_metric_for_tooltip`
  8. `test_legend_lists_before_and_after`
- Update the `test_html_assembler` integration test that checks the JSON key: `refactor_dashboard_json` → `pipeline_health_dashboard_json`.

---

## 6. Build Script + html_assembler Wiring

### 6.1 `scripts/build_hr_report.py` changes

- **Remove**: `get_git_lines_before`, `get_git_lines_after`, `get_module_stats` (the 3 module-metric collectors), and the call to `build_refactor_bar`. They served the old Section 4.
- **Keep**: `get_test_count_before` (parses the ab40b09 baseline test file) and the `uv run pytest --collect-only` call (now used to fill `test_coverage.after`).
- **Add**: import `pipeline_metrics`, build the `metrics` tuple with `TEST_COVERAGE_TEMPLATE` patched in, call `build_pipeline_health_dashboard(metrics)`.
- **Update** the `assemble_html` call:
  - old: `refactor_bar_b64=..., module_graph_svg=..., refactor_stats={...}`
  - new: `module_graph_svg=...` (kept), `pipeline_health_dashboard_json=<new>`, `refactor_stats={...}` (shrinks to just the test_before / test_after pair, since the dashboard now carries the 4 metrics).

The `static_charts.py` `build_refactor_bar` function is **no longer called** and can be removed (with its tests in `test_static_charts.py` updated accordingly — see §7).

### 6.2 `html_assembler.py` changes

`assemble_html()` signature change:

```python
def assemble_html(
    results_root: Path,
    module_graph_svg: str,
    pipeline_health_dashboard_json: dict,   # NEW (replaces refactor_dashboard_json)
    refactor_stats: dict,                    # smaller: {test_before, test_after}
) -> str:
```

**Removed keyword**: `refactor_bar_b64` (no longer needed — `build_refactor_bar` is gone, the new dashboard carries the metric visualization inline).

**Removed helper**: `_build_refactor_dashboard_data(refactor_stats: dict)` at `html_assembler.py:86-119` — its only consumer (the old `build_refactor_dashboard` call) is removed.

**Template render context**: replace `refactor_dashboard_json` → `pipeline_health_dashboard_json`.

**Call sites in `tests/test_visualization/test_html_assembler.py`** that must be updated (verified by grep):
- Lines 8, 43: drop `build_refactor_bar` import and the `refactor_bar_b64=...` kwarg.
- Line 71: assertion `"Engineering excellence" in html` → replace with `"Robust AI Pipeline Engineering" in html`.
- Line 130: assertion `"x-data" in html and "showGraph" in html` → drop (the `x-data` wrapper is removed per §6.3 M4).
- Lines 134-156 (`test_refactor_chart_inlined`): rename to `test_pipeline_health_chart_inlined`, update assertions to look for `"echarts-pipeline-health-dashboard"`, `"Stochastic-to-Deterministic Defense"`, `"Memory-Safe Streaming"`, `"Comprehensive Observability"`, and `"pipelineHealthDashboard"`.
- ~28 `assemble_html(...)` call sites: drop the `refactor_bar_b64=...` kwarg everywhere it appears.

### 6.3 Template wiring (M4 — must delete dead `x-data` and click-handler shim)

`template.py` Section 4 currently has a `x-data="{ showGraph: false }"` wrapper and a `bindDashboardClickHandler()` JS function (lines 322, 509-530) that targets the OLD metric name "Architectural Decoupling" and pokes at `root._x_dataStack[0]` (an Alpine internal). The new design replaces both with a clean Alpine store + a single `chart.on('click', ...)` handler attached to the new dashboard.

**Edits to `template.py`** (in addition to the §3.2 / §5.4 changes):
- **Remove** the `x-data="{ showGraph: false }"` wrapper div around the ECharts container at line 322.
- **Remove** the inner `<div x-show="showGraph" ...>` block at lines 330-338; replace with the new `x-show="$store.pipelineUi.showDeepDive"` block per §3.2.
- **Remove** the `bindDashboardClickHandler()` function definition (lines 509-530) and its call from `DOMContentLoaded` (line 540).
- **Replace** with a new click-binding step inside the existing `rebuildAllCharts()` function (or as a sibling function called once after the dashboard is initialized):
  ```javascript
  function bindPipelineHealthClickHandler() {
    const el = document.getElementById('echarts-pipeline-health-dashboard');
    if (!el || !window.__hrCharts['echarts-pipeline-health-dashboard']) return;
    const chart = window.__hrCharts['echarts-pipeline-health-dashboard'];
    chart.on('click', function () {           // any bar, any metric
      window.__hrToggleDeepDive();
    });
  }
  ```
  And call `bindPipelineHealthClickHandler()` at the end of `rebuildAllCharts()`.
- **Remove** the `window.__hrAppState = { showGraph: false };` declaration at line 415 (no longer needed — the new `Alpine.store('pipelineUi', ...)` replaces it).
- Section 4 `<div id="echarts-pipeline-health-dashboard">` (renamed per §3.2).
- The JS init block:
  ```javascript
  buildChart('echarts-pipeline-health-dashboard', window.__hrOpts.pipelineHealthDashboard);
  ```
- The new Alpine store + `__hrToggleDeepDive` function (per §5.4).

---

## 7. Test Plan Summary

| New / Updated | File | Tests | Purpose |
|---|---|---|---|
| New | `tests/test_visualization/test_pipeline_metrics.py` | 5 | `PipelineMetric` dataclass invariants, `ALL_STATIC_METRICS` shape, `TEST_COVERAGE_TEMPLATE` shape |
| Updated | `tests/test_visualization/test_echarts.py` | `TestPipelineHealthDashboard` (8 tests) replaces `TestRefactorDashboard` | Title, X-axis, colors, hidden Y-axis, label formatter, tooltip formatter, metric-in-data, legend |
| Updated | `tests/test_visualization/test_html_assembler.py` | ~5–10 assertion edits (no method count change) | Drop `refactor_bar_b64` kwarg at 28 call sites, rename DOM id and narrative copy, drop `x-data`/`showGraph` assertion at line 130, replace "Engineering excellence" with "Robust AI Pipeline Engineering" at line 71 (per §6.2) |
| Updated | `tests/test_visualization/test_static_charts.py` | drop `TestRefactorBar` tests; keep `TestModuleGraphSvg` | `build_refactor_bar` is removed |
| Unchanged | `tests/test_visualization/test_module_graph.py` | n/a | AST discovery is reused as-is |

**Total visualization test count delta** (verified by source-file inspection):
- `+5` new tests in `test_pipeline_metrics.py`
- `+8` new tests in `TestPipelineHealthDashboard`
- `−4` removed tests in `TestRefactorDashboard` (the old class, 4 methods)
- `−2` removed tests in `TestBuildRefactorBar` (`test_static_charts.py:13-29`, 2 methods)
- `~5–10` edits in `test_html_assembler.py` for renamed DOM id, kwargs, narrative copy (count varies by helper functions)
- **Net delta**: +7 tests, with `test_html_assembler.py` accumulating assertion-only edits (no method count change).

---

## 8. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Hardcoded metric values drift from reality | Medium | Each `PipelineMetric.note` documents the original measurement method + date. Re-measurement is a manual `git grep` task; add a `docs/superpowers/specs/2026-06-19-section-4-metrics-recheck.md` follow-up. |
| Hidden module graph renders at 0×0 on first reveal | Medium | `__hrToggleDeepDive` calls `Alpine.nextTick(() => echarts.getInstanceByDom(el).resize())` (per §5.4). Covered by manual test in 3 browsers (Chrome, Firefox, Safari). |
| Bar labels overflow on narrow viewports | Low | X-axis `interval: 0` + label `formatter` wraps to 2 lines (`\n` between words) when the name > 18 chars. CSS `.engineering-layout-grid` collapses to 1 column at < 900px. |
| Spec-card copy reads as hype / unverified | Low | Each claim cites a concrete artifact: `LLMResponseParseError` (real exception class in `src/tcfd_extractor/evaluation/exceptions.py:24`), `TCFD_BATCH_WORKERS=8` (real config in `src/tcfd_extractor/config.py:6`), `EvaluationResult.model_validate(...)` (real Pydantic call in `src/tcfd_extractor/evaluation/evaluator.py:69`), 329+ tests (auto-computed from pytest). |
| Old `build_refactor_dashboard` reference leaks | Low | `grep` check in DoD: `rg "refactor_dashboard|refactor-bar" src/ tests/` must return 0 matches. |
| Alpine store `pipelineUi` collides with another library | Low | Project-namespaced (`pipelineUi`, parallel to existing `hrApp`); only consumed by `__hrToggleDeepDive`. No external script defines `window.Alpine.store.pipelineUi`. |
| "Before (god-class)" legend label is too informal | Low | Captures the truth of the story (it WAS a god class). If user prefers "Before (monolith)" / "After (modular)", it's a 1-line string change in §5.1. |

---

## 9. Out of Scope

- No new ECharts dashboards (this spec only rebuilds Section 4).
- No changes to Sections 1, 2, 3, 5 of the HR report.
- No new dependencies — uses existing ECharts + Alpine.js + Jinja2.
- No new test infrastructure — extends existing `tests/test_visualization/`.
- No i18n changes — Section 4 is English-only.
- No mobile-specific design beyond the 1-column fallback in the CSS grid.
- No changes to the `output/hr_report/README.md` deployment instructions.
- No GitHub Pages URL change.
- No re-measurement of the 3 hardcoded metrics (out of scope; follow-up spec).

---

## 10. Definition of Done

A task is "DONE" only when ALL of the following are true:

- [ ] `src/tcfd_extractor/visualization/pipeline_metrics.py` exists with `PipelineMetric` dataclass, `MEMORY_FOOTPRINT`, `CONCURRENCY`, `SCHEMA_COMPLIANCE`, `ALL_STATIC_METRICS`, `TEST_COVERAGE_TEMPLATE`
- [ ] `tests/test_visualization/test_pipeline_metrics.py` passes (5 tests)
- [ ] `build_pipeline_health_dashboard(metrics)` exists in `echarts.py`; old `build_refactor_dashboard` is removed
- [ ] `TestPipelineHealthDashboard` in `tests/test_visualization/test_echarts.py` passes (8 tests); no `TestRefactorDashboard` references remain anywhere in the repo
- [ ] `tests/test_visualization/test_static_charts.py` no longer tests `build_refactor_bar`; `build_module_graph_svg` tests still pass
- [ ] `template.py` Section 4 uses `id="echarts-pipeline-health-dashboard"`, 2-column `engineering-layout-grid`, 3 spec-cards with the exact copy from §3.2
- [ ] CSS additions from §3.3 are present in the `<style>` block
- [ ] `Alpine.store('pipelineUi', { showDeepDive: false })` is registered on `alpine:init`
- [ ] `window.__hrToggleDeepDive` is defined and uses `Alpine.nextTick` + `echarts.getInstanceByDom(el).resize()` (per §5.4)
- [ ] **M4 (dead-code removal)**: `x-data="{ showGraph: false }"` wrapper div is removed from Section 4; `bindDashboardClickHandler()` function and its `DOMContentLoaded` call are removed; `window.__hrAppState = { showGraph: false }` declaration is removed
- [ ] **M4 (new click handler)**: `bindPipelineHealthClickHandler()` is defined and called from `rebuildAllCharts()`; it attaches `chart.on('click', () => window.__hrToggleDeepDive())` to the new dashboard
- [ ] `scripts/build_hr_report.py` calls the new builder, removes `build_refactor_bar` plumbing, passes `pipeline_health_dashboard_json`
- [ ] `src/tcfd_extractor/visualization/html_assembler.py` accepts and renders the new dashboard JSON; `refactor_bar_b64` keyword and `_build_refactor_dashboard_data` helper are removed
- [ ] `rg "refactor_dashboard|refactor-bar|build_refactor_bar|TestRefactorDashboard|__hrAppState|bindDashboardClickHandler" src/ tests/ scripts/` returns 0 matches
- [ ] `rg "_build_refactor_dashboard_data" src/` returns 0 matches
- [ ] `uv run pytest tests/test_visualization/ -v` passes
- [ ] `python scripts/build_hr_report.py --output output/hr_report/` succeeds and `scripts/check_leakage.py` exits 0
- [ ] **SC-4 manual test** (cannot be automated in pytest without a Selenium harness): open `output/hr_report/index.html` in **3 browsers** (Chrome, Firefox, Safari). For each browser: (1) confirm 8 bars render with the correct colors (`#8b3a3a` for Before, `#56d364` for After) and per-bar labels; (2) click one bar from each of the 4 metric groups (total 4 clicks) and confirm the module graph (`#echarts-module-graph`) appears; (3) click the same bar again to confirm the graph collapses; (4) open DevTools, evaluate `echarts.getInstanceByDom(document.getElementById('echarts-module-graph'))` after the graph is revealed, and confirm a non-null ECharts instance is returned (proves the `resize()` call worked). Record results in `output/hr_report/BUILD_LOG.md` under "Section 4 manual test".
- [ ] No real company name appears anywhere in the new Section 4 copy or in `output/hr_report/index.html` (verified by `scripts/check_leakage.py` exit 0)
- [ ] `output/hr_report/index.html` is regenerated and the new Section 4 visually matches §3.2

---

## 11. Open Questions (Resolved in brainstorming 2026-06-19)

| Question | Resolution |
|---|---|
| Replace 4 old metrics with 4 new, or keep all 8? | **Replace — 4 new metrics** (Memory, Concurrency, Schema Compliance, Test Coverage) |
| How to source the metric values? | **Hybrid**: test count auto (pytest), the other 3 hardcoded with method comments |
| Which bar triggers the deep-dive? | **Any bar** in the chart |
| Chart title? | **"AI Pipeline Resilience & Engineering Health"** |
| ECharts DOM id? | **Renamed** to `echarts-pipeline-health-dashboard` |
| Y-axis: shared numeric scale? | **No** — hidden; per-bar `label` shows formatted value with unit |
| Hidden graph resize on Alpine reveal? | **Yes** — `Alpine.nextTick` + `echarts.resize()` |
| Old `build_refactor_dashboard` removed or kept? | **Removed** (no parallel builder; single source of truth) |
| ECharts builder signature? | `(metrics, theme)` to match other 4 builders and integrate with `applyTheme()`; uses `_get_base_option()` for theme inheritance |
| Alpine store name? | **`pipelineUi`** (project-namespaced, parallel to `hrApp`) |
| `refactor_bar_b64` kwarg on `assemble_html`? | **Removed** (the new dashboard carries the metric visualization inline) |
| `_build_refactor_dashboard_data` helper in `html_assembler.py`? | **Removed** (its only consumer is gone) |
| `x-data="{ showGraph: false }"` wrapper in `template.py`? | **Removed** (replaced by `Alpine.store('pipelineUi', ...)`) |
| `bindDashboardClickHandler()` JS function? | **Removed and replaced** by `bindPipelineHealthClickHandler()` (any-bar click → `__hrToggleDeepDive`) |
| `window.__hrAppState`? | **Removed** (replaced by `Alpine.store('pipelineUi', ...)`) |
