"""One-way company_id anonymization for HR report.

Maps a company_id (e.g. "000001") to a stable but irreversible label
(e.g. "Company #042") using a SHA-256 hash. The hash space is large
enough that brute-force reversal is impractical for the report's audience.

The original company_id is NEVER recoverable from the anonymized label.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

_YEAR_RE = re.compile(r"(\d{4})年")


def anonymize_company_id(company_id: str) -> str:
    """Map a company_id to a stable, irreversible label."""
    if not company_id:
        company_id = "__empty__"
    digest = hashlib.sha256(company_id.encode("utf-8")).hexdigest()[:6]
    bucket = int(digest, 16) % 1000
    return f"Company #{bucket:03d}"


def anonymize_filename(filename: str) -> str:
    """Map a real filename to a sanitized label."""
    basename = Path(filename).name
    match = _YEAR_RE.search(basename)
    year = match.group(1) if match else "0000"
    stem = Path(basename).stem
    digest = hashlib.sha256(stem.encode("utf-8")).hexdigest()[:4]
    suffix = int(digest, 16) % 1000
    return f"report_year{year}_#{suffix:03d}.md"


def anonymize_record(record: dict) -> dict:
    """Return a copy of `record` with sensitive fields anonymized."""
    out = dict(record)
    if "file" in out:
        out["file"] = anonymize_filename(out["file"])
    if "reason" in out and isinstance(out["reason"], str):
        out["reason"] = out["reason"][:80]
    return out