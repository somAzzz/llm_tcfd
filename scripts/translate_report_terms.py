#!/usr/bin/env python3
"""Translate report chart terms with a local sglang OpenAI-compatible server.

The generated file is read by:
    src/tcfd_extractor/visualization/translations.py

Typical usage:
    uv run python scripts/translate_report_terms.py
    uv run python scripts/build_report.py --output output/report/

The script is intentionally strict:
    - LLM output must parse as JSON.
    - Pydantic validates every translated label.
    - Values must be English-only public chart labels.
    - Existing translations are reused so the job can resume after interruption.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from tcfd_extractor.config import llm_settings
from tcfd_extractor.visualization.translations import BASE_KEYWORD_TRANSLATIONS, has_cjk


DEFAULT_OUTPUT = Path("src/tcfd_extractor/visualization/llm_translations.json")
DEFAULT_CLUSTERS_DIR = Path("output/tcfd_keywords/phase5_category_mapping")
DEFAULT_EVAL_DIR = Path("output/evaluate_cooccurrence")
DEFAULT_YEARS = [2022, 2023, 2024]

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_ASCII_LABEL_RE = re.compile(r"[^A-Za-z0-9+&/ .,:;()%-]+")
_GENERIC_LABELS = {
    "english label",
    "translation",
    "translated term",
    "term",
    "label",
    "english translation",
}


class TranslationMap(BaseModel):
    """Validated translation payload from the LLM or from disk."""

    translations: dict[str, str] = Field(default_factory=dict)

    @field_validator("translations")
    @classmethod
    def validate_translations(cls, value: dict[str, str]) -> dict[str, str]:
        cleaned: dict[str, str] = {}
        for source, target in value.items():
            source = str(source).strip()
            raw_target = str(target).strip()
            if has_cjk(raw_target):
                raise ValueError(f"translation for {source!r} still contains Chinese: {raw_target!r}")
            target = normalize_label(raw_target)
            if not source:
                raise ValueError("translation key cannot be empty")
            if not target:
                raise ValueError(f"empty translation for {source!r}")
            if len(target) < 2:
                raise ValueError(f"translation for {source!r} is too short: {target!r}")
            if len(target) > 80:
                raise ValueError(f"translation for {source!r} is too long: {target!r}")
            if target.lower() in _GENERIC_LABELS:
                raise ValueError(f"translation for {source!r} is a generic placeholder: {target!r}")
            cleaned[source] = target
        return cleaned

    def require_terms(self, expected_terms: list[str]) -> None:
        missing = [term for term in expected_terms if term not in self.translations]
        if missing:
            sample = ", ".join(repr(x) for x in missing[:5])
            raise ValueError(f"LLM response missing {len(missing)} terms: {sample}")


class TranslationFile(BaseModel):
    """Final on-disk translation file contract."""

    translations: dict[str, str]

    @model_validator(mode="after")
    def validate_file(self) -> "TranslationFile":
        TranslationMap(translations=self.translations)
        return self


def normalize_label(value: str) -> str:
    """Normalize a candidate English chart label."""
    value = value.strip().strip('"').strip("'")
    value = _CJK_RE.sub("", value)
    value = _ASCII_LABEL_RE.sub(" ", value)
    value = re.sub(r"\s+", " ", value).strip(" -_/")
    return value


def english_fallback(term: str) -> str:
    """Stable English-only fallback used only after LLM retries fail."""
    ascii_part = normalize_label(term)
    if len(ascii_part) >= 2 and re.search(r"[A-Za-z]{2,}", ascii_part):
        return ascii_part.title()
    digest = hashlib.sha1(term.encode("utf-8")).hexdigest()[:6].upper()
    return f"Climate Disclosure Term {digest}"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_candidate_terms(
    *,
    clusters_dir: Path,
    eval_dir: Path,
    years: list[int],
    include_known: bool = False,
) -> list[str]:
    """Collect Chinese labels that can appear in Sunburst and Network charts."""
    priority: Counter[str] = Counter()

    for path in sorted(clusters_dir.glob("*_clusters.json")):
        data = _load_json(path)
        if not isinstance(data, list):
            continue
        for cluster in data:
            if not isinstance(cluster, dict):
                continue
            cluster_size = int(cluster.get("size") or len(cluster.get("keywords", [])) or 1)
            label = str(cluster.get("math_label") or "").strip()
            if _should_translate(label, include_known=include_known):
                priority[label] += 1000 + cluster_size
            for keyword in cluster.get("keywords", []):
                keyword = str(keyword).strip()
                if _should_translate(keyword, include_known=include_known):
                    priority[keyword] += min(cluster_size, 100)

    for year in years:
        jsonl = eval_dir / str(year) / "results.jsonl"
        if not jsonl.exists():
            continue
        with jsonl.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not row.get("is_tcfd_related"):
                    continue
                for field in ("keyword_a", "keyword_b"):
                    keyword = str(row.get(field) or "").strip()
                    if _should_translate(keyword, include_known=include_known):
                        priority[keyword] += 1

    return [term for term, _ in priority.most_common()]


def _should_translate(term: str, *, include_known: bool) -> bool:
    if not term or not _CJK_RE.search(term):
        return False
    return include_known or term not in BASE_KEYWORD_TRANSLATIONS


def load_existing_translations(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    raw = _load_json(path)
    if isinstance(raw, dict) and "translations" in raw:
        raw = raw["translations"]
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return TranslationMap(translations=raw).translations


def extract_json_objects(text: str) -> list[dict[str, Any]]:
    """Extract every usable JSON object from an LLM response.

    Qwen reasoning traces often echo the prompt's example JSON before the final
    answer.  We keep all objects here and choose the best candidate later,
    instead of trusting the first brace pair in the response.
    """
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    decoder = json.JSONDecoder()
    objects: list[dict[str, Any]] = []
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            objects.append(obj)
    if not objects:
        raise ValueError(f"No JSON object found in LLM response: {text[:200]!r}")
    return objects


def parse_translation_response(text: str, expected_terms: list[str]) -> dict[str, str]:
    errors: list[str] = []
    best_ordered: dict[str, str] | None = None
    best_exact: dict[str, str] | None = None
    for obj in extract_json_objects(text):
        translations = obj.get("translations", obj)
        if not isinstance(translations, dict):
            errors.append("JSON response must be an object or contain a translations object")
            continue
        try:
            validated = TranslationMap(translations=translations)
        except (ValidationError, ValueError) as exc:
            errors.append(str(exc))
            continue
        matched = [term for term in expected_terms if term in validated.translations]
        if len(matched) == len(expected_terms):
            best_exact = {term: validated.translations[term] for term in expected_terms}
            continue
        if len(validated.translations) == len(expected_terms):
            best_ordered = dict(zip(expected_terms, validated.translations.values(), strict=True))
        errors.append(f"candidate covered {len(matched)}/{len(expected_terms)} expected terms")

    if best_exact is not None:
        return best_exact
    if best_ordered is not None:
        return best_ordered
    raise ValueError("; ".join(errors[-3:]) or "No valid translation JSON candidate found")


def build_prompt(terms: list[str]) -> str:
    return (
        "/no_think\n"
        "Translate these Chinese climate, energy, environmental, and industrial "
        "disclosure terms into concise professional English chart labels.\n"
        "Return only one compact JSON object. The object keys must be exactly the "
        "Chinese terms in the input list, and each value must be the English label.\n"
        "Rules:\n"
        "- Include every source term exactly as a key.\n"
        "- Values must contain no Chinese characters.\n"
        "- Preserve acronyms such as ESG, VOCs, CO2, PV, LNG, LED, SCR.\n"
        "- Prefer 2 to 6 words. Use Title Case.\n"
        "- Do not explain, reason, or wrap the JSON in markdown.\n\n"
        f"Input terms:\n{json.dumps(terms, ensure_ascii=False)}"
    )


def translate_batch(
    *,
    client: OpenAI,
    model: str,
    terms: list[str],
    temperature: float,
    max_tokens: int,
    disable_thinking: bool,
) -> dict[str, str]:
    extra_body = None
    if disable_thinking:
        extra_body = {
            "chat_template_kwargs": {"enable_thinking": False},
            "separate_reasoning": False,
        }
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise terminology translator for climate finance reports. "
                    "Output valid JSON only."
                ),
            },
            {"role": "user", "content": build_prompt(terms)},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        extra_body=extra_body,
    )
    content = response.choices[0].message.content or ""
    return parse_translation_response(content, terms)


def write_translations(path: Path, translations: dict[str, str]) -> None:
    validated = TranslationFile(translations=dict(sorted(translations.items())))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(validated.translations, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Translate report chart terms with local sglang and Pydantic validation."
    )
    parser.add_argument("--base-url", default=llm_settings.base_url)
    parser.add_argument("--api-key", default=llm_settings.api_key)
    parser.add_argument("--model", default=llm_settings.model_name)
    parser.add_argument("--timeout", type=int, default=llm_settings.timeout)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument(
        "--enable-thinking",
        action="store_true",
        help="Allow Qwen reasoning output. By default the script asks sglang to disable it.",
    )
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--retry-delay", type=float, default=1.0)
    parser.add_argument("--limit", type=int, default=0, help="Translate only the first N terms.")
    parser.add_argument("--years", type=int, nargs="+", default=DEFAULT_YEARS)
    parser.add_argument("--clusters-dir", type=Path, default=DEFAULT_CLUSTERS_DIR)
    parser.add_argument("--eval-dir", type=Path, default=DEFAULT_EVAL_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--include-known", action="store_true", help="Retranslate manual terms too.")
    parser.add_argument("--force", action="store_true", help="Ignore existing output translations.")
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Fail instead of writing stable English fallbacks after retry exhaustion.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Collect terms but do not call the LLM.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.batch_size <= 0:
        raise ValueError("--batch-size must be positive")

    terms = collect_candidate_terms(
        clusters_dir=args.clusters_dir,
        eval_dir=args.eval_dir,
        years=args.years,
        include_known=args.include_known,
    )
    if args.limit:
        terms = terms[:args.limit]

    existing = {} if args.force else load_existing_translations(args.output)
    pending = [term for term in terms if term not in existing]

    print(f"Collected {len(terms):,} candidate terms")
    print(f"Existing translations: {len(existing):,}")
    print(f"Pending translations: {len(pending):,}")
    print(f"Model: {args.model} @ {args.base_url}")

    if args.dry_run:
        for term in pending[:50]:
            print(term)
        return 0

    client = OpenAI(base_url=args.base_url, api_key=args.api_key, timeout=args.timeout)
    translations = dict(existing)
    total_batches = (len(pending) + args.batch_size - 1) // args.batch_size

    for batch_index, start in enumerate(range(0, len(pending), args.batch_size), 1):
        batch = pending[start:start + args.batch_size]
        for attempt in range(1, args.max_retries + 1):
            try:
                translated = translate_batch(
                    client=client,
                    model=args.model,
                    terms=batch,
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                    disable_thinking=not args.enable_thinking,
                )
                translations.update(translated)
                print(f"Batch {batch_index}/{total_batches}: translated {len(batch)} terms")
                break
            except (ValidationError, ValueError, Exception) as exc:
                print(
                    f"Batch {batch_index}/{total_batches} attempt {attempt} failed: "
                    f"{type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )
                if attempt < args.max_retries:
                    time.sleep(args.retry_delay * attempt)
                    continue
                if args.no_fallback:
                    return 1
                fallback = {term: english_fallback(term) for term in batch}
                TranslationMap(translations=fallback)
                translations.update(fallback)
                print(f"Batch {batch_index}/{total_batches}: wrote validated fallbacks")

        write_translations(args.output, translations)

    write_translations(args.output, translations)
    print(f"Wrote {len(translations):,} translations to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
