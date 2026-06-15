# CLAUDE.md — dqar-aidbox
*Digital Quality Audit Readiness — Aidbox-Side Sandbox*
*Last updated: June 2026 | Confidential — Internal*

---

## What This Project Is

The Aidbox-side component of the DQAR platform. Receives the egress package from
`dqar-client-kit` (anonymized extract + conformance reports), loads into Aidbox
with full AuditEvent provenance metadata, runs SQL on FHIR semantic assessment,
and generates three-tier findings reports.

**Project boundary:** Everything from S3 inward. No PHI (Path B) or PHI under
plan BAA (Path C). No client-side conformance testing code.

---

## Aidbox / FHIR Infrastructure Reference

> See @docs/aidbox-kb.md for all Aidbox, SQL on FHIR, and FHIR API implementation details.

---

## Sister Repos

| Repo | Role |
|---|---|
| `dqar-contracts` | Shared schemas, ViewDefinitions, SQL, EXT definitions. Source of truth for the client–sandbox interface. |
| `dqar-client-kit` | Client-side conformance testing kit. Produces the egress package this repo consumes. |

**Dependency:** `dqar-contracts>=1.0.0,<2.0.0` is installed into this repo's venv.
During development: `pip install -e ../dqar-contracts`.
In CI/prod: install from private package registry.

**Never import from `dqar-client-kit` directly.** Consume the egress package only.

---

## Architecture Position

```
CLIENT ENVIRONMENT (dqar-client-kit)         THIS REPO (dqar-aidbox)
────────────────────────────────           ────────────────────────────────
Stage 1  Conformance testing          →    S3 presigned PUT URL (web/presign.py)
Stage 2  PHI redaction (Path B)            ↓
         egress package (tar.gz)      →    Stage 3  Load to Aidbox  (stage3/load.py)
                                           ↓
                                          Stage 4  SQL on FHIR assessment (stage4/)
                                           ↓
                                          Stage 5  Findings report (stage5/)
```

---

## Seven AuditEvent Extension Fields

EXT 1–5 from inference algorithm (`stage3/inference.py`).
EXT 6–7 from pipeline orchestrator, set once before the resource loop begins.

| EXT | URL | Source |
|---|---|---|
| EXT 1 | `http://indicina.com/fhir/ext/source-type` | `infer_source_metadata()` |
| EXT 2 | `http://indicina.com/fhir/ext/source-system-id` | `infer_source_metadata()` |
| EXT 3 | `http://indicina.com/fhir/ext/source-feed-id` | `infer_source_metadata()` |
| EXT 4 | `http://indicina.com/fhir/ext/source-inference-confidence` | `infer_source_metadata()` |
| EXT 5 | `http://indicina.com/fhir/ext/ecds-ssor` | Derived from EXT 1 |
| EXT 6 | `http://indicina.com/fhir/ext/ingest-pipeline-id` | Orchestrator |
| EXT 7 | `http://indicina.com/fhir/ext/ol-run-id` | Orchestrator (ingest batch tag) |

**EXT 7 is an ingest batch tag, not a Marquez join key.** Marquez has been dropped.
OpenLineage `RunEvent`s go directly to OpenMetadata. See `shared/lineage.py`.

---

## Project Structure

```
dqar-aidbox/
├── stage3/
│   ├── provision.py        # Per-engagement Aidbox org + OAuth client provisioning
│   ├── load.py             # S3 download → inference → atomic bundle POST → lineage emit
│   └── inference.py        # Source-type inference algorithm (Priority 0-6)
├── stage4/
│   └── semantic_assessment.py  # SQL measures loaded from dqar-contracts; AuditEvent joins
├── stage5/
│   └── findings.py         # Three-tier findings report generation
├── pipeline/
│   └── ingest/
│       └── bulk_export.py  # FHIR server → NDJSON export utility
├── web/
│   ├── app.py              # S3 presigned upload portal
│   ├── presign.py
│   └── templates/upload.html
├── shared/
│   ├── engagement.py       # Re-export shim → dqar_contracts.shared.engagement
│   └── lineage.py          # OpenLineage RunEvent → OpenMetadata (not Marquez)
├── init_bundle/
│   ├── generate.py         # CI: generates init-bundle.json from dqar-contracts
│   └── init-bundle.json    # Generated — do not hand-edit
├── viewdefs/               # Symlinked or CI-copied from dqar-contracts at deploy
├── specs/                  # Reference copies for Claude Code context (not source of truth)
├── docs/
│   └── aidbox-kb.md
└── config/
    └── engagements/        # Gitignored
```

---

## Init Bundle

The Aidbox Init Bundle is generated from `dqar-contracts` at CI time:

```bash
python init_bundle/generate.py
```

Never hand-edit `init_bundle/init-bundle.json`. It is regenerated on every deploy.
All ViewDefinitions in the bundle have `getResourceKey()` enforced by the generator.

---

## Measure SQL

Stage 4 loads parallel SQL reconstruction queries from `dqar-contracts`:

```python
from stage4.semantic_assessment import _load_measure_sql
cbp_sql = _load_measure_sql("cbp_numerator")
```

The SQL queries project `observation_id` (or equivalent resource key) for the
lineage chain. CQL produces the population rate; SQL reconstruction produces the
same rate plus resource-level evidence. Disagreement is a Tier 2 finding.

---

## Multitenancy

Single Aidbox instance (Multibox). Per-engagement isolation via Organization-scoped
AccessPolicies. One Organization resource per engagement, created by `stage3/provision.py`.

---

## Key Spec Files

| File | Contents |
|---|---|
| `docs/aidbox-kb.md` | Aidbox platform reference |
| `specs/dqar-05-source-inference-algorithm.md` | Full Priority 0-6 inference spec |
| `specs/dqar-05-amendment-priority-0-provenance.md` | Priority 0 Provenance lookup |
| `specs/dqar-06-uc1-app-technical-specification.md` | Full pipeline spec Stage 3–5 |

---

## Development Principles

1. **Atomic bundle requirement is inviolable.** Resource + AuditEvent in one transaction bundle. No separate POSTs.
2. **EXT 1–5 from inference, EXT 6–7 from orchestrator.** Never reverse this.
3. **Unknown source-type is a finding, not a suppressed error.** Log it. Surface it in findings.
4. **Init Bundle is generated from contracts.** Never hand-edit init-bundle.json.
5. **SQL measures come from dqar-contracts.** Never hardcode measure SQL in this repo.
6. **OpenLineage → OpenMetadata directly.** Marquez is dropped. ol-run-id is a batch tag only.
7. **Client testers get FHIR API credentials only.** Never issue /$sql access to clients.

---

## Unanswered Questions — Confirm With Health Samurai

1. Does Aidbox's CQL evaluation engine generate AuditEvents or Provenance resources referencing resources consumed during measure calculation?
2. Does Aidbox support auto-generation of Provenance resources on ingest?
3. Does Interbox support the typed/testable/modular mapping pattern described at DevDays 2026?
4. Termbox standalone licensing terms for plans with existing FHIR servers.
