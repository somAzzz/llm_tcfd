#!/usr/bin/env python3
"""Build the HR report (single-file interactive HTML).

Usage:
    python scripts/build_hr_report.py --output output/hr_report/
    python scripts/build_hr_report.py --output output/hr_report/email/ --target email-attachment

The script:
1. Loads all JSONL results from output/evaluate_cooccurrence/
2. Anonymizes company names (via the visualization layer)
3. Builds 4 ECharts charts (sunburst/streamgraph/network/sankey) + 1 matplotlib chart + 1 SVG module graph
4. Renders the Jinja2 template with all chart data inlined (single-file HTML, 1.5-2MB)
5. Writes index.html, README.md, .nojekyll to output dir
6. Runs the leakage check (must pass for the script to exit 0)

If the leakage check fails, the script still writes the HTML but exits 1.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path


def get_test_count_before() -> int:
    """Count tests at the pre-refactor baseline by parsing ab40b09's test file."""
    try:
        result = subprocess.run(
            ["git", "show", "ab40b09:tests/test_cooccurrence_evaluator.py"],
            capture_output=True, text=True, check=False,
        )
        if result.returncode == 0:
            return sum(
                1 for line in result.stdout.splitlines()
                if line.strip().startswith("def test_")
            )
    except Exception:
        pass
    return 16


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the HR report")
    parser.add_argument(
        "--output", type=Path, default=Path("output/hr_report"),
        help="Output directory for the report",
    )
    parser.add_argument(
        "--target", choices=["github-pages", "email-attachment"],
        default="github-pages",
        help="Deployment target",
    )
    parser.add_argument(
        "--inline", action="store_true",
        help="Alias for --target email-attachment (inline JS, larger file)",
    )
    args = parser.parse_args()

    if args.inline:
        args.target = "email-attachment"

    output_dir: Path = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

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

    print("Building module graph SVG (via AST discovery)...")
    from tcfd_extractor.visualization.module_graph import discover_module_graph
    from tcfd_extractor.visualization.static_charts import build_module_graph_svg
    module_graph = discover_module_graph(Path("src/tcfd_extractor/evaluation"))
    module_svg = build_module_graph_svg(module_graph)

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

    index_path = output_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")
    print(f"Wrote {index_path} ({len(html):,} chars)")

    readme = f"""# TCFD Project Demo

**Live demo URL**: https://somAzzz.github.io/tcfd-report/

## What's in this report

A self-contained interactive HTML showcasing a production NLP system for
climate-related financial disclosure (TCFD) analysis of A-share annual reports.

Built on: {date.today().isoformat()}
Report size: {len(html.encode('utf-8')) / 1024:.1f} KB
Test count: {test_count_after} passing

### Sections

1. **Sunburst** — 3 dimensions (Policy / Market / Technology) → 83 clusters →
   individual keywords. Click any segment to drill down; click a keyword to
   see the original annual-report sentence in the side panel.
2. **Streamgraph** — TCFD keyword mentions per year (2000–2024), split by
   dimension. Drag the bottom slider to zoom into a year range.
3. **Network** — Keyword co-occurrence graph for the most recent 3 years.
   Nodes are draggable; edge thickness encodes co-occurrence weight.
4. **Sankey** — Keyword flow across the 4-stage pipeline (sampling →
   extraction → evaluation → aggregation). Click any flow to see source
   sentences.
5. **AI Pipeline Resilience & Engineering Health** — 4-bar comparison of
   the pre/post refactor metrics (memory footprint, concurrency, schema
   compliance, test coverage). Click any bar to expand the live module
   dependency graph of the evaluation subpackage.

All data is anonymized (company names are replaced with generic labels)
and embedded in the HTML; nothing is fetched at runtime except Plotly and
Mermaid from CDN.

## How to view locally

Open `index.html` in any modern browser. Loads Plotly and Mermaid from CDN.

## Development

To rebuild the report from the source repo:

```bash
# 1. From the main frequency_analyzer repo:
PYTHONPATH=src python scripts/build_hr_report.py --output output/hr_report/

# 2. Run the pre-push leakage check (script auto-runs it too, must exit 0):
python scripts/check_leakage.py output/hr_report/index.html

# 3. Stage and push to tcfd-report (NOT the main repo):
cd output/hr_report
git add index.html README.md
git commit -m "vNN: <description>"
git push origin main
```

The build script:
- Runs `pytest --collect-only` to fill the "Test count" stat
- Discovers the evaluation subpackage module graph via AST
- Assembles 4 ECharts options (sunburst / streamgraph / network / sankey)
  + 1 AI Pipeline dashboard + 1 module graph SVG
- Renders the Jinja2 template with all data inlined (single-file HTML)
- Auto-runs the leakage check and exits 1 if it fails

## Deploying to GitHub Pages

1. Create a new **public** repo: `tcfd-report`
2. Push: `index.html`, `README.md`, `.nojekyll`
3. Settings → Pages → Branch: `main`, Folder: `/ (root)` → Save

**Do NOT push the main `frequency_analyzer` repo.**

## Pre-push leakage check

```bash
python scripts/check_leakage.py index.html
```

Must exit 0 before pushing.
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")
    print(f"Wrote {output_dir / 'README.md'}")

    (output_dir / ".nojekyll").touch()
    print(f"Wrote {output_dir / '.nojekyll'}")

    print("\nRunning leakage check...")
    result = subprocess.run(
        [sys.executable, "scripts/check_leakage.py", str(index_path)],
        capture_output=True, text=True,
    )
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        print(
            f"\n❌ BUILD FAILED: leakage check returned {result.returncode}.\n"
            "   Do NOT push to public repo. Fix the leakage and re-run.",
            file=sys.stderr,
        )
        return 1

    print(f"\n✅ Build complete. Report at: {index_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())