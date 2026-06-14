# CLAUDE.md — Indicina DQAR-UC4 Data Lineage Platform
*Digital Quality Audit Readiness — Aidbox / AWS environment*
*Last updated: June 2026 | Confidential — Internal*

---

## What This Project Is

DQAR-UC4 is the **Indicina-operated backend** of the DQAR Assessment pipeline. It receives anonymized FHIR extracts uploaded by client-side UC1, loads them into Aidbox with full AuditEvent provenance metadata, runs SQL on FHIR semantic assessment, and generates three-tier findings reports.

**Project boundary:** Everything from S3 inward. No PHI. No client-side code.

For the client-side conformance kit (Stage 1 + Stage 2), see `../dqar-uc1`.

---

## Architecture Position

```
CLIENT ENVIRONMENT (PHI — dqar-uc1)         INDICINA / AIDBOX (anonymized — this repo)
─────────────────────────────────           ────────────────────────────────────────────
Stage 1a  Bulk FHIR API preflight      →    S3 presigned PUT URL (web/presign.py)
Stage 1b  NDJSON structural check            ↓
Stage 1c  US Core conformance          →    Stage 3  Load to Aidbox  (stage3/load.py)
Stage 2   PHI redaction                      ↓
          tar.gz upload via UI         →    Stage 4  SQL on FHIR assessment (stage4/)
                                             ↓
                                            Stage 5  Findings report (stage5/)
```

---

## Aidbox / FHIR Infrastructure Reference

> For all development work involving Aidbox, SQL on FHIR, access control, subscriptions, MCP tools, or Aidbox configuration — see @docs/aidbox-kb.md

---

## Seven AuditEvent Extension Fields (Canonical — dqar-05 authoritative)

Every resource loaded into Aidbox is posted as a **single atomic FHIR transaction bundle** together with an AuditEvent carrying all seven extensions. No separate writes.

| Extension URL | Field | EXT | Source |
|---|---|---|---|
| `http://indicina.com/fhir/ext/source-type` | source-type | EXT 1 | Inference algorithm |
| `http://indicina.com/fhir/ext/source-system-id` | source-system-id | EXT 2 | Inference algorithm |
| `http://indicina.com/fhir/ext/source-feed-id` | source-feed-id | EXT 3 | Inference algorithm |
| `http://indicina.com/fhir/ext/source-inference-confidence` | source-inference-confidence | EXT 4 | Inference algorithm |
| `http://indicina.com/fhir/ext/ecds-ssor` | ecds-ssor | EXT 5 | Derived from EXT 1 via SSoR mapping |
| `http://indicina.com/fhir/ext/ingest-pipeline-id` | ingest-pipeline-id | EXT 6 | Pipeline orchestrator (uuid.uuid4() at run start) |
| `http://indicina.com/fhir/ext/ol-run-id` | ol-run-id | EXT 7 | OpenLineage start_run() UUID |

**EXT 1–5** are produced by `infer_source_metadata()` in `specs/dqar-05-source-inference-algorithm.md`.
**EXT 6–7** are set once by the pipeline orchestrator before the resource loop begins — not by the inference algorithm.

---

## Multitenancy Model

Single Aidbox instance (Multibox). Per-engagement isolation via Organization-scoped AccessPolicies at the FHIR API layer.

- **One Organization resource per engagement** — created by `stage3/provision.py`
- **Two OAuth clients per engagement** — `{eng-id}-ingest` (write, pipeline use only) and `{eng-id}-read` (read-only, sent to client tester)
- **Direct SQL (`/$sql`) is not exposed to clients** — org-scoping applies only at the FHIR API layer

---

## OpenLineage Integration

- `shared/lineage.py` emits OpenLineage RunEvents to Marquez / OpenMetadata
- `ol_run_id` UUID from `start_run()` becomes EXT 7 on every AuditEvent loaded in that run
- This creates a bidirectional join: AuditEvent → lineage graph → measure component output
- Required for DQAR provenance maturity Level 3+

---

## S3 Upload Portal

`web/` is a FastAPI application that:
1. Serves `GET /upload/{engagement_id}` — generates a presigned S3 PUT URL and renders the drag-drop UI
2. Exposes `GET /api/presign/{engagement_id}` — refreshes the URL if the page has been open a while
3. Exposes `GET /api/status/{engagement_id}` — checks whether `extract.tar.gz` has landed in S3

**Run:** `uvicorn web.app:app --reload --port 8000`

S3 bucket CORS must allow PUT from the portal origin before browser uploads work. See `web/presign.py` for the required CORS config.

---

## Engagement Config Schema

Engagement configs live in `config/engagements/{engagement_id}.json` (gitignored — contain credentials).

Required S3 fields for UC4:
```json
{
  "name": "eng-clienta-jun26",
  "server_type": "aidbox",
  "base_url": "https://dqar-sandbox.aidbox.app",
  "client_id": "eng-clienta-ingest",
  "client_secret": "...",
  "s3_bucket": "dqar-sandbox",
  "s3_prefix": "engagements/eng-clienta-jun26",
  "s3_region": "us-east-1",
  "s3_upload_expiry": 172800,
  "organization_id": "org-eng-clienta-jun26",
  "display_name": "Acme Health Plan"
}
```

---

## Project Structure

```
dqar-uc4/
├── shared/
│   ├── engagement.py       Auth adapter (copied from dqar-uc1; keep in sync)
│   ├── ingest.py           build_ingest_bundle() — assembles resource + AuditEvent bundle
│   └── lineage.py          LineageEmitter — OpenLineage start/end run
├── stage3/
│   ├── provision.py        Per-engagement Aidbox provisioning (Organization + OAuth clients)
│   └── load.py             S3 download → inference → bundle POST → lineage emit
├── stage4/
│   └── semantic_assessment.py   SQL on FHIR queries for 5 priority measures
├── stage5/
│   └── findings.py         Three-tier findings report generation
├── web/
│   ├── app.py              FastAPI — upload portal routes
│   ├── presign.py          S3 presigned URL generation + status check
│   └── templates/
│       └── upload.html     Drag-drop client upload UI
├── init_bundle/
│   └── init-bundle.json    Aidbox Init Bundle (platform config — StructureDefinitions, AccessPolicies)
├── viewdefs/
│   └── *.json              SQL on FHIR ViewDefinitions (measure lineage, source summary)
├── config/
│   ├── engagement.schema.json
│   └── engagements/        (gitignored — contain credentials)
├── specs/                  Reference copies of shared KB specs
└── docs/
    └── aidbox-kb.md        Aidbox platform reference
```

---

## Development Principles

- **No PHI ever enters this environment.** Stage 2 anonymization runs in the client environment before upload.
- **Atomic bundle requirement is inviolable.** Every resource and its AuditEvent must be a single FHIR transaction bundle POST. `build_ingest_bundle()` in `shared/ingest.py` is the only sanctioned assembly path.
- **EXT 1–5 from inference, EXT 6–7 from orchestrator.** Never reverse this. Never set EXT 6/7 inside the inference algorithm.
- **Unknown source-type is a finding, not an error.** Log it, include it in findings, do not suppress.
- **Client testers get FHIR API credentials only.** Never issue `/$sql` access to clients — org-scoping does not apply at the SQL layer.
- **Assessment phase is vendor-neutral.** Aidbox and Termbox appear in the roadmap phase, not in assessment findings output.

---

## Key Spec Files

| File | Contents |
|---|---|
| `docs/aidbox-kb.md` | Aidbox platform architecture, APIs, SQL on FHIR, MCP tools |
| `specs/dqar-05-source-inference-algorithm.md` | Full inference algorithm — EXT 1–5 derivation |
| `specs/dqar-06-uc1-app-technical-specification.md` | Full UC1 pipeline spec including Stage 3–5 |
| `specs/DQAR_Bulk_FHIR_Extract_Specification_v2_0.md` | Extract format, 7-extension AuditEvent spec |

---

## Unanswered Questions — Confirm With Health Samurai

1. Does Aidbox's CQL evaluation engine generate AuditEvents or Provenance resources referencing resources consumed during measure calculation?
2. Does Aidbox support auto-generation of Provenance resources on ingest (companion Provenance on every POST from an external system)?
3. Termbox standalone licensing terms for plans with existing FHIR servers.
