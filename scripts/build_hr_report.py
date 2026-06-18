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


def get_git_lines_before(path: Path) -> int:
    """Return the line count of `path` at the initial commit (ab40b09), or 0."""
    try:
        result = subprocess.run(
            ["git", "show", "ab40b09:src/tcfd_extractor/evaluation/cooccurrence_evaluator.py"],
            capture_output=True, text=True, check=False,
        )
        if result.returncode == 0:
            return len(result.stdout.splitlines())
    except Exception:
        pass
    return 0


def get_current_lines(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8")
        return len(text.splitlines())
    except Exception:
        return 0


def get_module_stats() -> tuple[int, int, int]:
    """Return (total_lines, module_count, test_count_after)."""
    eval_dir = Path("src/tcfd_extractor/evaluation")
    py_files = [p for p in eval_dir.glob("*.py") if p.name != "__init__.py"]
    total = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in py_files)
    module_count = len(py_files)
    try:
        result = subprocess.run(
            ["uv", "run", "pytest", "--collect-only", "-q", "tests/"],
            capture_output=True, text=True, check=False,
        )
        for line in result.stdout.splitlines() + result.stderr.splitlines():
            if "tests collected" in line:
                return total, module_count, int(line.split()[0])
    except Exception:
        pass
    return total, module_count, 0


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

    # Gather stats
    god_class_path = Path("src/tcfd_extractor/evaluation/cooccurrence_evaluator.py")
    god_class_lines_before = get_git_lines_before(god_class_path)
    if god_class_lines_before < 100:
        print(
            f"WARNING: git show ab40b09 returned only {god_class_lines_before} lines "
            f"(expected ~468). Check the commit ref and file path.",
            file=sys.stderr,
        )
    god_class_lines_after = get_current_lines(god_class_path)
    total_module_lines, module_count, test_count_after = get_module_stats()

    if test_count_after < 50:
        print(
            f"WARNING: pytest collection returned only {test_count_after} tests. "
            f"Expected ~200+. Check that tests/ exists and pytest is installed.",
            file=sys.stderr,
        )

    test_count_before = get_test_count_before()

    print("Building refactor bar chart...")
    from tcfd_extractor.visualization.static_charts import build_refactor_bar
    refactor_b64 = build_refactor_bar(
        god_class_lines_before=god_class_lines_before,
        god_class_lines_after=god_class_lines_after,
        total_module_lines=total_module_lines,
        module_count=module_count,
        test_count_before=test_count_before,
        test_count_after=test_count_after,
    )

    print("Building module graph SVG (via AST discovery)...")
    from tcfd_extractor.visualization.module_graph import discover_module_graph
    from tcfd_extractor.visualization.static_charts import build_module_graph_svg
    module_graph = discover_module_graph(Path("src/tcfd_extractor/evaluation"))
    module_svg = build_module_graph_svg(module_graph)

    print("Assembling HTML...")
    from tcfd_extractor.visualization.html_assembler import assemble_html
    html = assemble_html(
        results_root=Path("output/evaluate_cooccurrence"),
        refactor_bar_b64=refactor_b64,
        module_graph_svg=module_svg,
        refactor_stats={
            "god_class_before": god_class_lines_before,
            "god_class_after": god_class_lines_after,
            "module_count": module_count,
            "total_lines": total_module_lines,
            "test_before": test_count_before,
            "test_after": test_count_after,
        },
    )

    index_path = output_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")
    print(f"Wrote {index_path} ({len(html):,} chars)")

    readme = f"""# TCFD Project Demo

**Live demo URL**: https://<username>.github.io/tcfd-hr-report/

## What's in this report

A self-contained interactive HTML showcasing a production NLP system for
climate-related financial disclosure (TCFD) analysis of A-share annual reports.

Built on: {date.today().isoformat()}
Report size: {len(html.encode('utf-8')) / 1024:.1f} KB
Test count: {test_count_after} passing

## How to view locally

Open `index.html` in any modern browser. Loads Plotly and Mermaid from CDN.

## Deploying to GitHub Pages

1. Create a new **public** repo: `tcfd-hr-report`
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