# Output Directory Map

This document explains the current `output/` layout, the data flow between
directories, and which outputs are public-safe.

## Big Picture

```text
raw annual reports
  -> output/tcfd_keywords/
       keyword extraction, validation, clustering, summary CSV
  -> output/frequency/
       keyword frequency CSVs, co-occurrence context, trend charts
  -> output/evaluate_cooccurrence/
       LLM evaluation results per year
  -> output/report/
       public GitHub Pages report generated from evaluated and clustered data
```

The public report is the only `output/` subtree intended to be pushed to a
public repository, and even that must pass `scripts/check_leakage.py` first.

## Canonical Outputs

### `output/tcfd_keywords/`

Role: keyword extraction and clustering pipeline output.

Produced by:
- `python -m tcfd_extractor.main`
- `python -m tcfd_extractor.clustering.main --input ... --output output/tcfd_keywords`

Important files:
- `tcfd_keywords_summary.csv` feeds the report Sankey chart.
- `phase1_ingestion/merged_vocabulary.json` is the merged vocabulary snapshot.
- `phase2_validation/validation_result.json` and `removed_keywords.json` are semantic validation results.
- `phase3_clustering/clustering_result.json` is the clustering output.
- `phase5_category_mapping/*_clusters.json` feeds the report sunburst chart.
- `samples/*.json` contains per-report extraction outputs and may include real company names.

Public safety: private by default. Do not publish.

### `output/frequency/`

Role: frequency and co-occurrence analysis output.

Produced by:
- `python -m tcfd_extractor.frequency.main --output-dir output/frequency`
- `python -m tcfd_extractor.frequency.visualization.plot_yearly_avg`
- `python scripts/merge_llm_stats.py`
- `python scripts/plot_llm_stats.py`

Important files:
- `词频统计_政策.csv`, `词频统计_市场.csv`, `词频统计_技术.csv`
- `cooccurrence_context/` contains markdown contexts consumed by evaluation.
- `dimension_yearly_avg.png` and `llm_dimension_yearly_avg.png` are derived charts.

Public safety: private by default. Context files may contain source text and company names.

### `output/evaluate_cooccurrence/`

Role: LLM-based TCFD relevance evaluation output.

Produced by:
- `python -m tcfd_extractor.evaluation.evaluate_cooccurrence`
- `python -m tcfd_extractor.evaluation.batch_evaluate_cooccurrence`

Important files:
- `<year>/results.jsonl` is the canonical per-year evaluation data.
- `<year>/summary.md` is the per-year summary.
- Root `results.jsonl` / `summary.md` are aggregate or older single-run outputs.

Consumed by:
- `scripts/build_report.py`
- `scripts/merge_llm_stats.py`

Public safety: private by default. Report generation anonymizes and samples from it.

### `output/report/`

Role: generated public-facing HTML report.

Produced by:
- `python scripts/build_report.py --output output/report/`

Consumes:
- `output/evaluate_cooccurrence/`
- `output/tcfd_keywords/tcfd_keywords_summary.csv`
- `output/tcfd_keywords/phase5_category_mapping/`
- `src/tcfd_extractor/evaluation/` for module graph discovery

Important files:
- `index.html`
- `README.md`
- `.nojekyll`

Special rule: this directory is itself a separate Git repository:
`git@github.com:somAzzz/tcfd-report.git`.

Public safety: publishable only after `scripts/check_leakage.py` passes.

## Experiment And Legacy Outputs

These directories are useful for reproducing old experiments but are not part
of the canonical report build path.

### `output/0402/` and `output/0402.zip`

Role: dated sample / validation snapshot from April 2.

Contents:
- `tcfd_unique_validated.json`
- `年报采样/*.md`

Public safety: private. Contains company names and report samples.

Recommended future home if you decide to move it:
`output/_archive/2026-04-02-sample-validation/`

### `output/sample_100/` and `output/sample_100.zip`

Role: 100-sample co-occurrence context experiment.

Public safety: private. Contains source contexts and company names.

Recommended future home:
`output/_experiments/sample_100/`

### `output/frequency_top100/` and `output/frequency_top100.zip`

Role: top-100 frequency/co-occurrence context experiment.

Public safety: private. Contains source contexts and company names.

Recommended future home:
`output/_experiments/frequency_top100/`

### `output/frequency_results/`

Role: older or alternate frequency CSV output.

Public safety: private by default.

Recommended future home:
`output/_legacy/frequency_results/`

### `output/frequency_test/`

Role: small test fixture output for frequency code.

Public safety: private by default, but low risk compared with context folders.

Recommended future home:
`output/_fixtures/frequency_test/`

### `output/tcfd_keywords_test/`

Role: small test fixture output for extraction/clustering code.

Currently used by:
- `tests/test_clustering/test_ingestion.py`

Public safety: private by default. Keep in place unless tests are updated.

Recommended future home after test migration:
`tests/fixtures/tcfd_keywords_test/`

### `output/analyze_tcfd_duplicates/`

Role: duplicate-analysis diagnostics.

Produced by:
- `scripts/resolve_tcfd_duplicates_fast.py` or related duplicate analysis runs.

Public safety: private by default.

Recommended future home:
`output/_diagnostics/analyze_tcfd_duplicates/`

## Keep / Regenerate / Archive

Keep as canonical:
- `output/tcfd_keywords/`
- `output/frequency/`
- `output/evaluate_cooccurrence/`
- `output/report/`

Regenerable:
- `output/report/`
- frequency charts under `output/frequency/*.png`
- merged LLM frequency stats if source evaluation results are present

Archive candidates:
- `output/0402/`
- `output/sample_100/`
- `output/frequency_top100/`
- `output/frequency_results/`
- zip snapshots at the root of `output/`

Do not publish publicly:
- everything under `output/` except the checked `output/report/` publication repo.

