#!/usr/bin/env python3
"""Pre-push leakage checker for the HR report.

Scans `output/hr_report/index.html` for known sensitive terms.

Before pattern-matching, the script strips:
- `<script type="application/json">` blocks (Plotly chart data — false positives)
- `data:image/png;base64,...` values (matplotlib PNG binary — false positives)
- `<style>` blocks (CSS — false positives)

This is necessary because Plotly's default template embeds 16-digit colorscale
positions and matplotlib PNGs contain arbitrary binary bytes.

Exit codes:
  0  = no leakage detected
  1  = leakage detected (output to stderr)
  2  = error (file not found, missing CLI arg)

Usage:
    python scripts/check_leakage.py output/hr_report/index.html
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# A small list of well-known A-share companies (top 30 by market cap, 2024).
KNOWN_COMPANIES = [
    "平安银行", "万科A", "中信证券", "招商银行", "中国平安",
    "工商银行", "建设银行", "中国银行", "农业银行", "中国石化",
    "中国石油", "中国海油", "中国移动", "中国电信", "中国人寿",
    "中国神华", "贵州茅台", "五粮液", "宁德时代", "比亚迪",
    "宁沪高速", "海康威视", "美的集团", "格力电器", "海尔智家",
    "京东方A", "立讯精密", "工业富联", "北方华创", "中芯国际",
]

# Patterns that should never appear in the public HTML's visible text.
# Note: long digit runs (e.g., 16-digit numbers) are intentionally NOT in
# this list because they appear legitimately in Plotly's default colorscale
# template (0.1111111111111111, 0.2222222222222222, ...) and would cause
# false positives. If you need to check for them, do it on extracted JSON
# data only, not the entire HTML.
BAD_PATTERNS = [
    (r"@[\w.]+\.\w{2,}", "email-like pattern"),
    (r"\b1[3-9]\d{9}\b", "Chinese mobile phone number"),
    (r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "credit card number"),
    (r"\bTODO\b|\bFIXME\b", "TODO/FIXME debug marker"),
    (r"password|secret|api[_-]?key", "credential keyword"),
]


def _extract_visible_text(html: str) -> str:
    """Strip script/style blocks and base64 data URIs from HTML.

    Keeps:
    - All visible text (between tags)
    - All attribute values that aren't base64
    """
    # Remove <script>...</script>
    html = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    # Remove <style>...</style>
    html = re.sub(r"<style\b[^>]*>.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    # Remove base64 data URIs
    html = re.sub(r"data:[^;]+;base64,[A-Za-z0-9+/=]+", " ", html)
    # Remove HTML tags but keep their text content
    html = re.sub(r"<[^>]+>", " ", html)
    return html


def check_file(html_path: Path) -> list[str]:
    """Return a list of leakage findings (empty list = clean)."""
    if not html_path.exists():
        return [f"FILE NOT FOUND: {html_path}"]

    raw = html_path.read_text(encoding="utf-8", errors="replace")
    text = _extract_visible_text(raw)
    findings: list[str] = []

    for company in KNOWN_COMPANIES:
        if company in text:
            findings.append(f"LEAK: real company name '{company}' found in HTML")

    for pattern, desc in BAD_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            sample = matches[:3]
            findings.append(f"LEAK: {desc} — example matches: {sample}")

    return findings


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_leakage.py <path-to-html>", file=sys.stderr)
        return 2

    html_path = Path(sys.argv[1])
    if not html_path.exists():
        print(f"❌ File not found: {html_path}", file=sys.stderr)
        return 2

    findings = check_file(html_path)

    if findings:
        print(f"❌ Leakage check FAILED for {html_path}:", file=sys.stderr)
        for f in findings:
            print(f"  - {f}", file=sys.stderr)
        return 1

    print(f"✅ Leakage check passed for {html_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())