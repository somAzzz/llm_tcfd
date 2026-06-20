#!/usr/bin/env python3
"""Inspect the generated output directory.

This script prints a compact manifest of first-level `output/` entries so the
generated-data boundary stays visible without committing private artifacts.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROLE_MAP = {
    "tcfd_keywords": {
        "role": "canonical keyword extraction / clustering output",
        "public": False,
        "depends_on": [],
        "consumed_by": ["output/report", "output/frequency"],
    },
    "frequency": {
        "role": "canonical frequency and co-occurrence output",
        "public": False,
        "depends_on": ["output/tcfd_keywords"],
        "consumed_by": ["output/evaluate_cooccurrence"],
    },
    "evaluate_cooccurrence": {
        "role": "canonical LLM evaluation output",
        "public": False,
        "depends_on": ["output/frequency/cooccurrence_context"],
        "consumed_by": ["output/report", "scripts/merge_llm_stats.py"],
    },
    "report": {
        "role": "public report publication repo",
        "public": "after leakage check",
        "depends_on": [
            "output/evaluate_cooccurrence",
            "output/tcfd_keywords/tcfd_keywords_summary.csv",
            "output/tcfd_keywords/phase5_category_mapping",
        ],
        "consumed_by": ["GitHub Pages"],
    },
    "tcfd_keywords_test": {
        "role": "test fixture output for extraction / clustering",
        "public": False,
        "depends_on": [],
        "consumed_by": ["tests/test_clustering/test_ingestion.py"],
    },
    "frequency_test": {
        "role": "test fixture output for frequency analysis",
        "public": False,
        "depends_on": [],
        "consumed_by": [],
    },
    "frequency_results": {
        "role": "legacy or alternate frequency CSV output",
        "public": False,
        "depends_on": [],
        "consumed_by": [],
    },
    "frequency_top100": {
        "role": "top-100 frequency experiment",
        "public": False,
        "depends_on": [],
        "consumed_by": [],
    },
    "sample_100": {
        "role": "100-sample co-occurrence experiment",
        "public": False,
        "depends_on": [],
        "consumed_by": [],
    },
    "0402": {
        "role": "dated sample / validation snapshot",
        "public": False,
        "depends_on": [],
        "consumed_by": [],
    },
    "analyze_tcfd_duplicates": {
        "role": "duplicate-analysis diagnostics",
        "public": False,
        "depends_on": [],
        "consumed_by": [],
    },
}


def _human_size(num_bytes: int) -> str:
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GB"


def _entry_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def _entry_file_count(path: Path) -> int:
    if path.is_file():
        return 1
    return sum(1 for p in path.rglob("*") if p.is_file())


def build_manifest(root: Path) -> dict:
    entries = []
    if not root.exists():
        return {"root": str(root), "entries": []}

    for path in sorted(root.iterdir(), key=lambda p: p.name):
        name = path.name
        base_name = name.removesuffix(".zip")
        role = ROLE_MAP.get(base_name, {})
        size = _entry_size(path)
        entries.append({
            "name": name,
            "type": "directory" if path.is_dir() else "file",
            "size_bytes": size,
            "size": _human_size(size),
            "file_count": _entry_file_count(path),
            "role": role.get("role", "archive or unclassified generated artifact"),
            "public": role.get("public", False),
            "depends_on": role.get("depends_on", []),
            "consumed_by": role.get("consumed_by", []),
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect output/ relationships")
    parser.add_argument("--root", type=Path, default=Path("output"))
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Optional path to write the manifest JSON.",
    )
    args = parser.parse_args()

    manifest = build_manifest(args.root)
    if args.json:
        args.json.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(f"Output root: {manifest['root']}")
    print("Name                         Size       Files  Role")
    print("-" * 78)
    for entry in manifest["entries"]:
        print(
            f"{entry['name'][:28]:28} "
            f"{entry['size']:>10} "
            f"{entry['file_count']:>7}  "
            f"{entry['role']}"
        )
    if args.json:
        print(f"\nWrote manifest: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

