# Miner KB v0.2 (HashInsight)

This package contains a structured knowledge base to power an "ops diagnosis → playbook" feature.

## What's inside
- schema.json: entity schema (Model / FaultSignature / Playbook / Prevention / Tuning / ErrorCodeDictionary)
- sources.json: curated sources (official docs prioritized)
- models.json: model/brand coverage (includes placeholders for onboarding)
- taxonomy.json: categories + common metrics
- signatures.json: expanded fault signatures (seed)
- playbooks.json: step-by-step SOPs
- preventions.json: preventative checks
- tunings.json: recommended setup adjustments
- error_codes/: vendor error-code dictionaries (seed)
- docs/diagnosis_flow.md: process diagram + UI mapping

## Intended pipeline (app-side)
1) Ingest miner telemetry/logs.
2) Extract signals (keywords/regex/metrics/codes).
3) Match FaultSignatures (priority + evidence score).
4) Output top diagnosis + Playbook + Prevention + Tuning.

## Notes
- This is a *seed* knowledge base. "100% coverage for all miners and all faults" is achieved by continuously ingesting:
  - official manuals / error-code PDFs
  - brand firmware release notes
  - your own incident history (ground truth)

## Manual ingestion (v0.3)

See `ingest/` for crawler + optional PDF extraction scripts.
- `ingest/config/sources.yaml`: root sources to crawl
- `ingest/crawl_manuals.py`: builds a metadata catalog (JSONL)
- `ingest/merge_manuals_into_kb.py`: merges catalog into KB `sources.json`
- `ingest/extract_pdf_text.py` (optional): download PDFs and chunk text for internal search

Default mode stores only links/metadata (copyright-safe).

## Bitmain log codes (Antminer)

Bitmain uses log-string prompts (kernel/diagnostic logs) rather than a single numeric error-code table.
See `error_codes/bitmain_antminer_log_codes_v1.json` and `ingest/extract_bitmain_log_codes.py`.
