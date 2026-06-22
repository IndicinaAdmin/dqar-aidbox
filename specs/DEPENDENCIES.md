# Dependencies

> Scope: `dqar-aidbox-databricks-kit` — the **ingest-time** kit that loads UC
> properties, emits OpenLineage RunEvents to OpenMetadata, and writes AuditEvent
> provenance (EXT 6 + 7). Distinct from `dqar-client-kit`, which is the
> assessment-time CLI.

## Shared Contract (Required)
- `dqar-contracts>=1.0.0,<2.0.0` — shared types (`Engagement`, `MeasureSpec`, `ViewDefinitionRef`, …) re-exported via `dqar_contracts.shared`. Never redefine these locally.

## Core (Required)
- `pydantic>=2.0` — models (IngestContext, DQARIngestFacet, load results)
- `databricks-sdk>=0.20.0` — **core, not optional**: applies UC `TBLPROPERTIES`, executes statements via SQL warehouse
- `openlineage-python>=1.9.0` — RunEvent construction (START/COMPLETE/FAIL) and facet typing
- `requests>=2.31.0` — POST RunEvents to the OpenMetadata ingestion endpoint; HTTP to Aidbox
- `tenacity>=8.2.0` — retry/backoff on OpenMetadata + Aidbox calls

## Aidbox / FHIR
- Aidbox reached over HTTP (transaction bundle POST). No Python Aidbox SDK is required; `requests` is sufficient. Token supplied by caller / secret manager — never hardcoded.

## Optional
- `python-dotenv>=1.0.0` — local-dev credential loading
- Terraform (external, not a Python dep) — CAB-reviewed UC property application; see `01-uc-properties-loading.md`

## Dev
- `pytest>=7.0`
- `pytest-cov>=4.1`
- `responses>=0.24.0` — mock OpenMetadata / Aidbox HTTP in tests
- `black>=23.0`
- `ruff>=0.1.0`
- `mypy>=1.0`

## Explicitly NOT dependencies
These belong to `dqar-client-kit`, not here — their presence would signal a misfiled file:
- `click` (no conformance CLI surface here; the ingest CLI is thin)
- `ndjson` (this kit ingests via Aidbox bundles, not by parsing extract NDJSON)
- `scikit-learn` (Level 5 anomaly detection is client-kit's job)
- `pandas` (no extract-level aggregation here)

## Notes
- **OpenMetadata, not Marquez.** No Marquez client dependency anywhere — the lineage backend on the Indicina side is OpenMetadata.
- `databricks-sdk` is required because UC property *loading* is this kit's Phase 1; in client-kit the same library is *optional* because client-kit only *generates* the file.
