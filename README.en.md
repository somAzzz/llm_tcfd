# TCFD Keyword Extraction System

> A Chinese-language NLP system for extracting **TCFD** (Task Force on Climate-related Financial Disclosures) keywords from annual reports of A-share listed companies in China, with subsequent co-occurrence analysis, semantic validation, K-Means clustering, and LLM-based TCFD relevance evaluation.

[中文版本](./README.md)

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Modules](#modules)
- [Data Assumptions](#data-assumptions)
- [Testing](#testing)
- [Development & Refactoring Log](#development--refactoring-log)
- [License](#license)

---

## Overview

This project is a **TCFD (Task Force on Climate-related Financial Disclosures) keyword extraction and analysis system** for annual reports of A-share listed companies in China. It identifies climate-related disclosures in report text and classifies extracted keywords across three dimensions: **Policy**, **Market**, and **Technology**.

The complete pipeline includes:

1. **Sampling & Chunking** — sample annual reports, split into semantic chunks at paragraph/sentence boundaries
2. **Keyword Extraction** — extract TCFD keywords via a local LLM (SGLang, Qwen3.5-35B-A3B)
3. **Co-occurrence Analysis** — count co-occurrence within windows or sentences
4. **Semantic Clustering** — K-Means clustering with sentence-transformers validation
5. **TCFD Evaluation** — LLM-based relevance evaluation across three TCFD dimensions, with summary generation

## Features

- **Multi-dimensional classification**: Policy / Market / Technology (the three TCFD pillars)
- **Local LLM inference**: OpenAI-compatible protocol against a local SGLang server
- **Concurrent batch processing**: ThreadPoolExecutor + tqdm with retry & graceful abort
- **Memory-safe streaming**: Generator-based loading for large inputs
- **Centralized configuration**: pydantic-settings v2 with environment variable overrides
- **Structured exception hierarchy**: fine-grained error types for caller handling
- **Zero subprocess dependency**: batch processing is fully in-process, testable, and importable

## Quick Start

### Requirements

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) (recommended package manager)
- A local SGLang service (or any OpenAI-compatible LLM endpoint)

### Install

```bash
# Clone the repository
git clone <repo-url>
cd frequency_analyzer

# Sync dependencies
uv sync            # runtime only
uv sync --dev      # include dev dependencies (recommended)
```

### Configuration

All settings have sensible defaults. Override via environment variables (optional):

```bash
export TCFD_LLM_BASE_URL="http://127.0.0.1:30000/v1"
export TCFD_LLM_MODEL_NAME="Qwen/Qwen3.5-35B-A3B"
export TCFD_LLM_API_KEY="sk-local"
export TCFD_LLM_TIMEOUT=60
export TCFD_LLM_TEMPERATURE=0.1

export TCFD_PATH_INPUT_ROOT="output/frequency/cooccurrence_context"
export TCFD_PATH_OUTPUT_ROOT="output/evaluate_cooccurrence"

export TCFD_BATCH_WORKERS=8
export TCFD_BATCH_MAX_RETRIES=3
export TCFD_BATCH_RETRY_DELAY=1.0
```

### Run

```bash
# Full pipeline
python -m tcfd_extractor.main

# Word-bag validation CLI
python -m tcfd_extractor --input <file> --output <file>

# Frequency analysis
python -m tcfd_extractor.frequency.main [options]

# Keyword clustering
python -m tcfd_extractor.clustering.main --input <dir> --output <dir>

# TCFD evaluation (single directory)
python -m tcfd_extractor.evaluation.evaluate_cooccurrence \
    --input-dir output/frequency/cooccurrence_context/2020 \
    --output output/evaluate_cooccurrence/2020/results.jsonl \
    --summary output/evaluate_cooccurrence/2020/summary.md

# TCFD evaluation (per-year batch)
python -m tcfd_extractor.evaluation.batch_evaluate_cooccurrence \
    --year 2020
```

## Architecture

```
src/tcfd_extractor/
├── main.py                              # Main pipeline entry
├── sampler.py                           # Annual-report sampling
├── chunker.py                           # Text chunking (paragraph/sentence boundaries)
├── extractor.py                         # LLM-based keyword extraction (OpenAI API)
├── executor.py                          # Thread-pool concurrent executor
├── evaluator.py                         # (legacy) evaluator entry
├── aggregator.py                        # Result aggregation / export
├── tcfd_word_bag_validator.py           # Word-bag validation CLI
├── config.py                            # Global config (LLM/Path/Batch Pydantic Settings)
├── evaluation/                          # Evaluation module (recently refactored)
│   ├── models.py                        # Pydantic data models
│   ├── parser.py                        # Markdown co-occurrence context parser
│   ├── prompts.py                       # LLM prompt constants
│   ├── evaluator.py                     # Single-context LLM evaluator
│   ├── batch.py                         # Batch evaluator (concurrent + streaming)
│   ├── summary.py                       # Statistics + summary generation
│   ├── exceptions.py                    # Custom exception hierarchy
│   ├── cooccurrence_evaluator.py        # Thin-shell re-export (backward-compat entry)
│   ├── evaluate_cooccurrence.py         # Single-directory evaluation CLI
│   └── batch_evaluate_cooccurrence.py   # Per-year batch evaluation CLI
├── frequency/                           # Word-frequency statistics
│   ├── counter.py                       # Keyword counting (per 10k chars normalized)
│   ├── parser.py                        # Annual-report filename parser
│   └── cooccurrence.py                  # Co-occurrence analysis (window & sentence modes)
└── clustering/                          # Keyword clustering
    ├── clustering.py                    # K-Means + silhouette-based K selection
    ├── validator.py                     # sentence-transformers semantic validation
    ├── label_generator.py               # Optional LLM-based cluster labeling
    └── exporter.py                      # Export + t-SNE visualization
```

## Modules

### 1. Keyword Extraction (`tcfd_extractor`)

- `main.py` — Main pipeline orchestration
- `sampler.py` — Sample annual reports by company/year
- `chunker.py` — Split long text into semantic chunks
- `extractor.py` — Call LLM to extract TCFD keywords
- `executor.py` — Thread-pool execution with semaphore control
- `aggregator.py` — Merge / dedupe results, export JSON / CSV

### 2. Frequency Statistics (`tcfd_extractor.frequency`)

- `counter.py` — Keyword counting, normalized per 10k characters
- `cooccurrence.py` — Co-occurrence analysis, supports fixed-window and sentence modes
- `parser.py` — Parse `{company_id}-{company_name}-{year}年年度报告.txt` filename format

### 3. Clustering (`tcfd_extractor.clustering`)

- `clustering.py` — K-Means clustering with auto-K selection (silhouette score)
- `validator.py` — Semantic validation via sentence-transformers
- `exporter.py` — Export clustering results and t-SNE visualization

### 4. Evaluation (`tcfd_extractor.evaluation`)

Refactored in 2026-06. The original 468-line god class has been decomposed into 8 focused modules (see "Development & Refactoring Log").

- `models.py` — Data models: `CooccurrenceContext` / `TCFDValidationResult` / `EvaluationResult` / `FileParseResult`
- `parser.py` — Co-occurrence context MD file parser (with path fallback)
- `prompts.py` — LLM prompt constants (evaluation / summary)
- `evaluator.py` — `CooccurrenceEvaluator`: single-context LLM evaluation with raw-response logging
- `batch.py` — `BatchEvaluator`: concurrent + streaming batch processing, fail-fast on unrecoverable error
- `summary.py` — `compute_statistics` + `generate_summary`
- `exceptions.py` — `EvaluationError` / `LLMEvaluationError` / `LLMUnavailableError` / `LLMResponseParseError` / `LLMTimeoutError`
- `cooccurrence_evaluator.py` — Thin shell re-export (backward-compat; new code should import from submodules directly)

### 5. Tools & Scripts (`scripts/`)

- `tcfd_word_bag_validator.py` — Word-bag validation CLI

## Data Assumptions

- **Annual reports** are stored at `/home/bo/projects/data/A股年报/` organized by year subdirectories.
- **Filename format**: `{company_id}-{company_name}-{year}年年度报告.txt` (underscores are also supported).
- **File type**: plain text (`.txt`).
- **Co-occurrence output**: Markdown (`.md`) files produced by `tcfd_extractor.frequency`.

## Testing

```bash
# Run all tests
uv run pytest

# Run a specific test file
uv run pytest tests/test_config.py

# Run a specific test directory
uv run pytest tests/test_frequency/

# Run with coverage
uv run pytest --cov=src/tcfd_extractor
```

Test organization:

- `tests/test_config.py` — Global config + thread-safety
- `tests/test_cooccurrence_evaluator.py` — Backward-compat tests (unchanged API)
- `tests/evaluation/` — Evaluation module unit + integration tests
  - `test_exceptions.py` — Exception hierarchy
  - `test_models.py` — Data models
  - `test_prompts.py` — Prompt constants
  - `test_parser.py` — Markdown parser
  - `test_evaluator.py` — Single LLM evaluator
  - `test_batch.py` — Batch evaluator
  - `test_summary.py` — Statistics + summary
  - `test_integration.py` — End-to-end integration
- `tests/test_frequency/` — Frequency statistics
- `tests/test_clustering/` — Clustering

## Development & Refactoring Log

### 2026-06: Evaluation Module Refactor

**Goal**: Decompose the 468-line god class in `src/tcfd_extractor/evaluation/cooccurrence_evaluator.py`, centralize configuration via Pydantic Settings, eliminate subprocess usage, and expand test coverage.

**Change summary**:

| Metric | Value |
|---|---|
| God-class line count | 468 → 79 (83% reduction) |
| New modules | 8 (evaluator / batch / summary / parser / prompts / models / exceptions / config) |
| New tests | 95+ |
| Total tests passing | 165 (target: 101) |
| New-module coverage | 95–100% |
| subprocess usage | 0 |
| `print()` usage | 0 |

**Key DoD checkpoints**:

- ✅ Full test suite passing (165 passed)
- ✅ New-module coverage ≥ 90%
- ✅ No subprocess calls
- ✅ No `print()` usage
- ✅ Thin shell ≤ 80 lines (target 50–60; actual 79, including backward-compat wrapper)
- ✅ Malformed-JSON defense (`LLMResponseParseError` + raw response logging)
- ✅ Config thread safety (concurrent reads)
- ✅ All 16 pre-existing backward-compat tests pass (Note: baseline fix and mock-path migration were applied with user approval, since the plan's literal "zero modification" promise was incompatible with pre-existing Pydantic v2 / `.parse()` API drift)

## Contributing

Issues and PRs welcome. Before submitting:

- All tests pass
- New features include tests
- Code style matches existing patterns
- Significant changes update this README

## License

For research use only.
