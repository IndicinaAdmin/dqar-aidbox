# UC1 Assessment App — Technical Specification
**Digital Measure Readiness Assessment Application**
*Version: June 2026 | For Claude Code + Health Samurai Implementation*

---

## Overview

This document specifies the technical architecture for the UC1 Digital Measure Readiness Assessment application. This application is the technical implementation of one tenet of the broader Digital Quality Audit Readiness (DQAR) — specifically Domain 6 (ECDS and dQM readiness) with elements of Domain 2 (value set conformance) and Domain 3 (data lineage tracing).

**Framework linkage:** This app implements UC1 of the DQAR use case index (`dqar-03-use-case-index.md`). The full DQAR framework, six audit domains, three-tier findings structure, regulatory timeline, and partner guides live in the DQAR Shared KB project. This application does not implement the full framework — it implements the technical pipeline that powers UC1 assessment engagements.

**Partners:** Health Samurai (Aidbox + Termbox), Sonian (pipeline, query library, findings report)

---

## Architecture Summary

The pipeline has six stages. Stage 1 (with substages 1a–1c) executes entirely in the client environment against PHI-containing data. Stage 2 (PHI redaction) is optional and client-initiated. Stages 3–6 execute in the Sonian or plan-owned Aidbox environment.

```
CLIENT ENVIRONMENT (PHI present)

  Stage 1:   Bulk FHIR Export and Conformance Testing
             The client's IT team runs the conformance testing kit against their
             FHIR vendor extract. Three substages run in sequence.
             All PHI stays within the client environment.
             Outputs: three JSON reports + three PDF renders.

    Stage 1a: Bulk FHIR API conformance    [stage1a_bulk_fhir_export_preflight.py]
              CapabilityStatement query · $export kick-off · manifest
              conformance check · output content-type check against Bulk Data
              Access IG STU2. Runs against the live FHIR vendor server.
              Skipped if $export not declared in CapabilityStatement.
              Output: stage1a-{engagement}.json

    Stage 1b: ndjson structural conformance testing  [stage1b_ndjson_validator.py]
              Parseable JSON · resourceType present · one resource per
              line · UTF-8 encoding · resourceType matches filename stem
              (Patient.ndjson must contain only Patient resources).
              Runs against the exported ndjson files.
              Output: stage1b-{engagement}.json + PDF render

    Stage 1c: FHIR R4 + US Core conformance [stage1c_fhir_uscore_validator.py]
              1c-i  — Base FHIR R4 (4.0.1) structural conformance testing (no IG)
              1c-ii — US Core 6.1.0 profile conformance testing
              --backend hapi-cli (default): HAPI Validator CLI, no server needed (Rung 1/2)
              --backend aidbox: Aidbox $validate REST API, engagement config required (Rung 3+)
              Output: stage1c-i-{engagement}.json + stage1c-ii-{engagement}.json

  → Client receives three JSON reports + three PDF renders.
  → Client decision point — three paths forward:

  PATH A — Stop here (no data leaves the plan)
            Act on findings using internal staff or Sonian advisory.
            No sandbox, no PHI redaction, no vendor contracts needed.
            Full value from Stage 1 findings at Rung 1.

  PATH B — Proceed to sandbox (anonymized extract only)
            Client runs Stage 2 PHI redaction locally, sends
            anonymized extract to Sonian Aidbox sandbox.
            Deeper validation: Termbox VSD conformance, AuditEvent
            metadata, SQL on FHIR queries, full three-tier findings
            report. No PHI crosses the boundary.
            Appropriate while HS HIPAA/SOC2 due diligence is in progress.

  PATH C — Full platform operational mode (PHI in Aidbox)
            After plan completes Health Samurai HIPAA BAA and SOC2
            review and contracts Aidbox, the Bulk FHIR extract loads
            directly to the plan's own Aidbox instance with full PHI.
            No anonymization step. Stage 1 becomes the pre-ingest
            quality gate for real operations.
            AuditEvent metadata captures lineage from day one.
            This is the target state — the platform ladder destination.

  Stage 2:  PHI redaction + anonymization   [PATH B ONLY — client-initiated]
            Client runs local redaction against the Bulk FHIR extract.
            Produces anonymized ndjson — no member-identifiable fields.
            Not required for Path A or Path C.
            Output: anonymized extract ready for Sonian delivery.

PHI BOUNDARY — PATH B ONLY
  Anonymized extract + Stage 1 reports cross to Sonian.
  Path C bypasses this boundary entirely — PHI loads directly
  to the plan's own contracted Aidbox instance.

SONIAN ENVIRONMENT — PATH B (anonymized sandbox)

  Stage 3:  Load to Aidbox sandbox
            (a) Re-run Stage 1b + 1c conformance testing on anonymized extract
                → confirms redaction did not corrupt structural integrity
                → creates permanent conformance baseline for this extract
            (b) Termbox $validate-code — US Core required bindings
                + HEDIS MP2025 VSD (369 value sets)
            (c) AuditEvent + seven extensions generated atomically per resource

  Stage 4:  DQAR SQL on FHIR assessment queries
            Five-measure SQL on FHIR ViewDefinition library.
            Risk stratification matrix from AuditEvent metadata.
            Measure attribution join queries.

  Stage 5:  Three-tier findings report generation
            Tier 1 — Governance gaps
            Tier 2 — Measure data gaps
            Tier 3 — Digital readiness gaps
            Each finding: technical severity + governance root cause
            + DAMA-DMBOK maturity score + remediation recommendation.

PLAN'S OWN AIDBOX INSTANCE — PATH C (full PHI operational mode)

  Stage 3:  Load to plan-contracted Aidbox instance (with PHI)
            Same pattern as Path B sandbox — Stage 1b + 1c re-run
            at ingest, Termbox VSD, AuditEvent seven extensions.
            This is real operations, not assessment.
            AuditEvent metadata is permanent production lineage.

  Stage 4+: Ongoing UC2 monitoring cadence applies.
            Sonian runs assessment queries against plan's Aidbox
            on scheduled cadence under $4K/month retainer.
```

---

## Client-Side Conformance Testing Kit (Stage 1 — Substages 1a, 1b, 1c)

### Deliverable to client at engagement kickoff

Sonian provides a conformance testing kit the client's IT team runs on their own infrastructure against raw PHI-containing ndjson. No PHI leaves the client environment. The kit produces three JSON reports and three PDF renders. The client decides independently whether to proceed to the optional PHI redaction (Stage 2) and Sonian sandbox (Stage 3) stages.

The kit supports two validator backends for Stages 1b and 1c:
- **HAPI Validator CLI** — default, no vendor contract required, runs anywhere Java is available (Rung 1 and Rung 2)
- **Aidbox** — available at Rung 3+ when the plan has Aidbox in production; provides native conformance testing at write time with richer error metadata

### Stage 1a — Bulk FHIR API conformance  `stage1a_bulk_fhir_export_preflight.py`

Tests the plan's FHIR server `$export` implementation live against the SMART Bulk Data Access IG STU2 before any data is exported. Six checks: CapabilityStatement declares `$export`, kick-off returns 202 Accepted, Content-Location header present, polling completes with 200, manifest contains `output[]` and `requiresAccessToken`, output files return `application/fhir+ndjson` content-type.

Skipped automatically if preflight reports `bulk_export_supported: false`.

Output: `stage1a-{engagement}.json`

### Stage 1b — ndjson structural conformance testing  `stage1b_ndjson_validator.py`

Validates every line of every ndjson file in the Bulk FHIR export: parseable JSON, `resourceType` present, one resource per line. Runs against raw PHI-containing export output. No PHI in the output report — aggregate counts and error descriptions only.

Output: `stage1b-{engagement}.json` + PDF render

### Stage 1c — FHIR R4 + US Core conformance  `stage1c_fhir_uscore_validator.py`

Two sub-passes:

```bash
# Rung 1/2 — HAPI Validator CLI (default, no FHIR server required)
python stage1c_fhir_uscore_validator.py \
  --ndjson-dir data/export \
  --engagement client-name \
  --backend hapi-cli \
  --validator-jar tools/validator_cli.jar

# Rung 3+ — Aidbox $validate REST API (engagement config required)
python stage1c_fhir_uscore_validator.py \
  --ndjson-dir data/export \
  --engagement config/engagements/client.json \
  --backend aidbox
```

Both produce identical output files:
- `stage1c-i-{engagement}.json` — base FHIR R4 results
- `stage1c-ii-{engagement}.json` — US Core 6.1.0 results

For `--backend hapi-cli`, sub-passes run sequentially via the HAPI Validator CLI JAR (set `FHIR_VALIDATOR_JAR` env var or pass `--validator-jar`). For `--backend aidbox`, each resource is POSTed to `{base_url}/fhir/{ResourceType}/$validate` and OperationOutcome issues are classified into 1c-i (base FHIR R4) or 1c-ii (US Core) based on whether a US Core profile URL appears in the issue diagnostics. The `--engagement` argument must be a path to an engagement config JSON when using `--backend aidbox`.

### Conformance report format (delivered to Sonian — no PHI)

```json
{
  "report_type": "fhir-conformance",
  "stage": "1c-ii",
  "validator": "hapi-cli",
  "validator_version": "6.3.x",
  "ig_version": "hl7.fhir.us.core#6.1.0",
  "us_core_version": "6.1.0",
  "fhir_version": "4.0.1",
  "engagement": "client-name",
  "run_timestamp": "2025-10-14T09:00:00Z",
  "summary": {
    "total_resources": 48230,
    "error_count": 847,
    "warning_count": 2341,
    "information_count": 5102
  },
  "by_resource_type": [
    {
      "resource_type": "Condition",
      "total": 12440,
      "errors": 234,
      "warnings": 891,
      "top_errors": [
        {"code": "MUST_SUPPORT", "element": "Condition.clinicalStatus", "count": 189},
        {"code": "BINDING", "element": "Condition.code", "count": 45}
      ]
    }
  ]
}
```

Field notes: `"validator"` is `"hapi-cli"` or `"aidbox"` depending on `--backend`. `"validator_version"` is present only for `hapi-cli` (extracted from HAPI CLI stderr). `"ig_version"` and `"us_core_version"` are present only in the 1c-ii report. Both backends produce structurally identical reports.

---

## Feed Manifest (Client Deliverable — Engagement Kickoff)

The feed manifest is the ground truth for feed-level traceability. Collected before extract generation.

```json
{
  "plan_id": "[pseudonymized at delivery]",
  "extract_date": "2025-10-14",
  "us_core_version": "6.1.0",
  "fhir_version": "4.0.1",
  "feeds": [
    {
      "feed_id": "epic-prod-org447",
      "feed_type": "ehr-fhir-bulk",
      "source_system_name": "Epic EHR",
      "source_system_type": "clinical_ehr",
      "files": ["Patient.ndjson", "Condition.ndjson", "Observation.ndjson",
                "Encounter.ndjson", "Procedure.ndjson"],
      "member_count": 4823,
      "notes": "Epic MyChart FHIR R4 bulk export, org 447"
    },
    {
      "feed_id": "claims-edw-prod",
      "feed_type": "administrative-claims",
      "source_system_name": "Claims EDW",
      "source_system_type": "administrative_claims",
      "files": ["ExplanationOfBenefit.ndjson", "Coverage.ndjson"],
      "member_count": 9847
    },
    {
      "feed_id": "labcorp-hl7v2",
      "feed_type": "lab-fhir-transformed",
      "source_system_name": "LabCorp",
      "source_system_type": "clinical_lab",
      "files": ["Observation-lab.ndjson", "DiagnosticReport.ndjson"],
      "member_count": 3201,
      "notes": "HL7v2 ORU transformed to FHIR via Interbox"
    }
  ]
}
```

**Absence of feed manifest** = Level 6 governance finding (metadata management maturity score 1).
**Resources from undeclared sources** = undeclared source finding (data governance gap).

---

## Aidbox Assessment Sandbox Configuration

### Required Health Samurai products

| Product | Role |
|---|---|
| Aidbox | FHIR R4 server + PostgreSQL store for anonymized extract |
| Termbox | Terminology server — MP2025 VSD + US Core 6.1.0 bindings |

### Aidbox configuration requirements

```yaml
# Aidbox sandbox configuration for DQAR UC1 assessment
fhir_version: R4
postgres:
  database: dqar_assessment
  
validation:
  # US Core 6.1.0 IG loaded on write
  igs:
    - hl7.fhir.us.core#6.1.0
    - hl7.fhir.uv.bulkdata#2.0.0
  
audit:
  # AuditEvent generation on every FHIR operation
  enabled: true
  
terminology:
  # Termbox endpoint for $validate-code
  termbox_endpoint: http://termbox:8080
```

### Termbox VSD configuration

Three modes for VSD access (client determines which applies):

| Mode | Description | BAA required |
|---|---|---|
| 1 — API reference | Client's Termbox instance, Sonian read-only API key | No (read-only access) |
| 2 — Client export | Client-provided VSD export loaded to sandbox, deleted at close | SOW clause required |
| 3 — JSON from dQM package | FHIR ValueSet resources from client's NCQA DCS package | No additional license |

---

## AuditEvent Extension Metadata (Seven Fields)

Generated by the Sonian ingest pipeline at Stage 3 load time. Not sourced from the client's FHIR server.

### Extension definitions

```json
[
  {
    "url": "http://Sonian.io/fhir/ext/source-type",
    "valueType": "valueCode",
    "vocabulary": {
      "tier_a": ["clinical_ehr", "administrative_claims", "administrative_encounter", "pharmacy_pbm", "clinical_lab", "payer_exchange", "clinical_immunization_registry"],
      "tier_b": ["clinical_phr", "pharmacy_specialty", "clinical_hie", "clinical_registry", "case_management", "disease_management"],
      "unresolvable": ["unknown"]
    },
    "source": "feed-manifest | meta.source | resource-inference",
    "confidence": "asserted | high | medium | low | unknown",
    "purpose": "Expanded 13-value vocabulary. Tier A structurally detectable; Tier B requires feed manifest or meta.source. Classifies originating source system type. Study Type 2 lineage analysis."
  },
  {
    "url": "http://Sonian.io/fhir/ext/source-system-id",
    "valueType": "valueString",
    "format": "feed-id from manifest | SHA256(meta.source)[:12] | topology-cluster-{hash} | unknown-{pipeline-id}-{resource-type}",
    "purpose": "Pseudonymized source system instance ID. Consistent across all resources from same source."
  },
  {
    "url": "http://Sonian.io/fhir/ext/ingest-pipeline-id",
    "valueType": "valueString",
    "format": "{pipeline-run-id}/{feed-id}/{batch-id}",
    "example": "dqar-20251014-001/epic-prod-org447/Condition.ndjson-chunk-003",
    "purpose": "Three-level traceability: run / feed / batch. Enables feed-level quality analysis."
  },
  {
    "url": "http://Sonian.io/fhir/ext/source-feed-id",
    "valueType": "valueString",
    "format": "feed_id from manifest | derived from meta.source | topology-cluster-{hash} | unknown",
    "example": "epic-prod-org447",
    "purpose": "Feed-level identifier independent of full pipeline composite. Primary key for feed-level findings queries."
  },
  {
    "url": "http://Sonian.io/fhir/ext/source-inference-confidence",
    "valueType": "valueCode",
    "vocabulary": ["asserted", "high", "medium", "low", "unknown"],
    "purpose": "Confidence tier for source-type inference. Proportion at each tier is a direct provenance maturity metric."
  },
  {
    "url": "http://Sonian.io/fhir/ext/ecds-ssor",
    "valueType": "valueCode",
    "vocabulary": ["EHR/PHR", "Administrative", "Clinical Registry/HIE", "Case/Disease Mgmt"],
    "mapping": "Derived from source-type via SSoR mapping rule in dqar-05-source-inference-algorithm.md",
    "purpose": "NCQA ECDS Source of Record (SSoR) category. Four-value NCQA vocabulary. Null when source-type = unknown — triggers Tier 1 governance finding. Enables SSoR distribution reporting across the extract."
  },
  {
    "url": "http://Sonian.io/fhir/ext/ol-run-id",
    "valueType": "valueString",
    "format": "UUID v4 (OpenLineage runId)",
    "example": "550e8400-e29b-41d4-a716-446655440000",
    "purpose": "Ingest batch tag (OpenLineage runId, UUID v4) stamped on every AuditEvent written during a run — not a join key into a lineage graph. OpenLineage RunEvents are emitted directly to OpenMetadata (Marquez has been dropped); OpenMetadata builds the lineage graph from each RunEvent's declared inputs/outputs. Enables mechanical execution of DQAR lineage studies — from AuditEvent walk upstream through field-level transformation facets; from OpenLineage graph walk downstream to MeasureReport references. Required for Level 3+ maturity on the DQAR provenance rubric."
  }
]
```

Seven extension fields: EXT 1 source-type · EXT 2 source-system-id · EXT 3 source-feed-id · EXT 4 source-inference-confidence · EXT 5 ecds-ssor · EXT 6 ingest-pipeline-id · EXT 7 ol-run-id.

### Atomic transaction bundle pattern

```json
{
  "resourceType": "Bundle",
  "type": "transaction",
  "entry": [
    {
      "resource": { "resourceType": "Condition", "id": "pat-abc123-cond-001", "..." },
      "request": { "method": "PUT", "url": "Condition/pat-abc123-cond-001" }
    },
    {
      "resource": {
        "resourceType": "AuditEvent",
        "type": { "system": "http://terminology.hl7.org/CodeSystem/audit-event-type", "code": "rest" },
        "recorded": "2025-10-14T09:22:00Z",
        "agent": [{ "requestor": true, "who": { "display": "dqar-ingest-pipeline" } }],
        "source": { "observer": { "display": "Sonian DQAR Sandbox" } },
        "entity": [{ "what": { "reference": "Condition/pat-abc123-cond-001" } }],
        "extension": [
          { "url": "http://Sonian.io/fhir/ext/source-type", "valueCode": "clinical_ehr" },
          { "url": "http://Sonian.io/fhir/ext/source-system-id", "valueString": "epic-prod-org447" },
          { "url": "http://Sonian.io/fhir/ext/ingest-pipeline-id", "valueString": "dqar-20251014-001/epic-prod-org447/Condition.ndjson-chunk-003" },
          { "url": "http://Sonian.io/fhir/ext/source-feed-id", "valueString": "epic-prod-org447" },
          { "url": "http://Sonian.io/fhir/ext/source-inference-confidence", "valueCode": "asserted" },
          { "url": "http://Sonian.io/fhir/ext/ecds-ssor", "valueCode": "EHR/PHR" },
          { "url": "http://Sonian.io/fhir/ext/ol-run-id", "valueString": "550e8400-e29b-41d4-a716-446655440000" }
        ]
      },
      "request": { "method": "POST", "url": "AuditEvent" }
    }
  ]
}
```

---

## Source-Type Inference Algorithm

Applied when feed manifest does not explicitly declare source-type for a resource and `meta.source` is absent. See `dqar-05-source-inference-algorithm.md` for full decision tree and Tier A/Tier B detectability framework.

### Quick reference

| Signal | Source-type | Confidence | SSoR |
|---|---|---|---|
| Feed manifest (any type) | as declared | asserted | per mapping |
| meta.source — EHR vendor URI | `clinical_ehr` | asserted | EHR/PHR |
| meta.source — PHR/patient-app URI | `clinical_phr` | asserted | EHR/PHR |
| meta.source — HIE/CommonWell/Carequality | `clinical_hie` | asserted | Clinical Registry/HIE |
| meta.source — registry URI | `clinical_registry` | asserted | Clinical Registry/HIE |
| meta.source — case management URI | `case_management` | asserted | Case/Disease Mgmt |
| meta.source — disease management URI | `disease_management` | asserted | Case/Disease Mgmt |
| meta.source — PBM URI | `pharmacy_pbm` | asserted | Administrative |
| meta.source — specialty pharmacy URI | `pharmacy_specialty` | asserted | Administrative |
| meta.source — lab URI | `clinical_lab` | asserted | Clinical Registry/HIE |
| meta.source — P2P/PDex URI | `payer_exchange` | asserted | EHR/PHR |
| meta.source — claims/billing URI | `administrative_claims` | asserted | Administrative |
| ExplanationOfBenefit / Claim / Coverage | `administrative_claims` | high | Administrative |
| MedicationDispense (PBM identifier) | `pharmacy_pbm` | high | Administrative |
| MedicationDispense (specialty identifier) | `pharmacy_specialty` | high | Administrative |
| Observation.category = laboratory | `clinical_lab` | high | Clinical Registry/HIE |
| Immunization.primarySource = false | `clinical_immunization_registry` | high | Clinical Registry/HIE |
| Immunization.primarySource = true or absent | `clinical_ehr` | high | EHR/PHR |
| Observation.category = vital-signs/exam/survey | `clinical_ehr` | high | EHR/PHR |
| Condition + SNOMED + verificationStatus=confirmed | `clinical_ehr` | medium | EHR/PHR |
| Condition + ICD-10 only, no verificationStatus | `administrative_claims` | medium | Administrative |
| Encounter + SNOMED + rich participants | `clinical_ehr` | medium | EHR/PHR |
| Encounter + CPT + no participants | `administrative_encounter` | medium | Administrative |
| Topology cluster match | cluster-derived | low | per cluster |
| No signals | `unknown` | unknown | None → Tier 1 finding |

**Tier B types** (`clinical_phr`, `clinical_hie`, `clinical_registry`, `case_management`, `disease_management`, `pharmacy_specialty`) are structurally indistinguishable from `clinical_ehr` at Priorities 3–6. They require feed manifest or `meta.source` declaration. Resources falling to `unknown` because of absent Tier B declaration are Tier 1 metadata management governance findings.

---

## SQL on FHIR Assessment Queries — Minimum Viable Library

Five priority measures for UC1 MVP. Each measure has four query types: denominator context check, measurement period window check, exclusion code context check, data source attribution check.

### Infrastructure

```sql
-- HEDIS VSD lookup function (Aidbox PostgreSQL)
-- Requires VSD loaded via Sonian VSD loader
CREATE OR REPLACE FUNCTION hedis_validate_code(
  p_code TEXT,
  p_system TEXT,
  p_value_set_oid TEXT
) RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM hedis_vsd
    WHERE code = p_code
    AND code_system = p_system
    AND value_set_oid = p_value_set_oid
    AND measurement_year = '2025'
  );
$$ LANGUAGE SQL;

-- Measure attribution join function
CREATE OR REPLACE FUNCTION get_resource_provenance(p_resource_ref TEXT)
RETURNS TABLE (
  source_type TEXT,
  source_feed_id TEXT,
  ecds_ssor TEXT,
  pipeline_id TEXT,
  inference_confidence TEXT,
  ol_run_id TEXT,
  ingest_timestamp TIMESTAMPTZ
) AS $$
  SELECT
    ext_src.value->>'valueCode',
    ext_feed.value->>'valueString',
    ext_ssor.value->>'valueCode',
    ext_pip.value->>'valueString',
    ext_conf.value->>'valueCode',
    ext_ol.value->>'valueString',
    (ae.resource->>'recorded')::timestamptz
  FROM auditevent ae
  CROSS JOIN LATERAL jsonb_array_elements(ae.resource->'extension') ext_src
  CROSS JOIN LATERAL jsonb_array_elements(ae.resource->'extension') ext_feed
  CROSS JOIN LATERAL jsonb_array_elements(ae.resource->'extension') ext_ssor
  CROSS JOIN LATERAL jsonb_array_elements(ae.resource->'extension') ext_pip
  CROSS JOIN LATERAL jsonb_array_elements(ae.resource->'extension') ext_conf
  CROSS JOIN LATERAL jsonb_array_elements(ae.resource->'extension') ext_ol
  WHERE ae.resource #>> '{entity,0,what,reference}' = p_resource_ref
  AND ext_src.value->>'url'  = 'http://Sonian.io/fhir/ext/source-type'
  AND ext_feed.value->>'url' = 'http://Sonian.io/fhir/ext/source-feed-id'
  AND ext_ssor.value->>'url' = 'http://Sonian.io/fhir/ext/ecds-ssor'
  AND ext_pip.value->>'url'  = 'http://Sonian.io/fhir/ext/ingest-pipeline-id'
  AND ext_conf.value->>'url' = 'http://Sonian.io/fhir/ext/source-inference-confidence'
  AND ext_ol.value->>'url'   = 'http://Sonian.io/fhir/ext/ol-run-id'
  LIMIT 1;
$$ LANGUAGE SQL;
```

### Priority measure stubs

**CBP — Controlling Blood Pressure**
- Denominator: members 18-85 with hypertension diagnosis (value set OID: 2.16.840.1.113883.3.464.1003.104.12.1003)
- Level 3 checks: outpatient or telehealth encounter type (class AMB or VR), measurement period date window, blood pressure Observation linked to qualifying encounter
- Key failure mode: encounter type constraint — inpatient BP readings should not qualify denominator

**CDC — Comprehensive Diabetes Care**
- Multiple numerators: HbA1c testing, HbA1c control, eye exam, kidney health evaluation, blood pressure
- Level 3 checks: HbA1c LOINC code in correct value set, result value in physiological range (4-15%), result date within measurement period, performing lab linked
- Key failure mode: HbA1c LOINC cross-mapping errors (lab-specific local codes not mapped to standard LOINC)

**COL-E — Colorectal Cancer Screening ECDS**
- Denominator: members 45-75
- Level 3 checks: age constraint applied at measurement period end, exclusion codes in correct context (colorectal cancer diagnosis, colectomy), screening procedure in correct value set
- Key failure mode: exclusion code applied to wrong encounter type silently suppressing eligible members

**BCS-E — Breast Cancer Screening ECDS**
- Denominator: women 50-74
- Level 3 checks: sex/gender constraint, 24-month lookback window for mammography, exclusion for bilateral mastectomy
- Key failure mode: 24-month window not applied — 12-month window used instead, inflating apparent compliance

**FUH/FUM — Follow-Up After Hospitalization**
- Denominator: members discharged from inpatient psychiatric facility
- Level 3 checks: discharge date as anchor for follow-up window (7 days / 30 days), follow-up encounter type constraint (outpatient mental health), encounter sequence logic
- Key failure mode: discharge date vs. admit date confusion — wrong anchor shifts measurement window

Full query implementations: `queries/level3/` directory in the UC1 app repo.

---

## Findings Report Structure

### Three-tier output

```json
{
  "engagement_id": "dqar-uc1-[plan-id]-2025",
  "assessment_date": "2025-10-14",
  "plan_size": "500K-2M",
  "findings": {
    "tier1_governance_gaps": [
      {
        "finding_id": "G1-001",
        "domain": "Domain 2 — Value Set Conformance",
        "description": "CBP denominator binding using MP2024 hypertension value set — 3 retired ICD-10 codes still active in production. No terminology governance process detected this drift across measurement periods.",
        "governance_root_cause": "Absent year-round VSD governance — no process to validate value set currency at NCQA release + 30 days",
        "severity": "HIGH",
        "affected_members": 1247,
        "rate_impact_estimate": "1.2 percentage points",
        "remediation_owner": "Terminology governance",
        "remediation_timeline": "Days to fix binding — weeks to implement governance process"
      }
    ],
    "tier2_measure_data_gaps": [],
    "tier3_digital_readiness_gaps": [
      {
        "finding_id": "T3-001",
        "domain": "Domain 6 — ECDS Readiness",
        "description": "No meta.source or Provenance resources present in extract. Source-type inferred for 89% of resources. Inference confidence: high 34%, medium 41%, low 14%, unknown 11%.",
        "severity": "MEDIUM",
        "mp2029_risk": "HIGH — NCQA provenance evaluation methodology hardening",
        "remediation_owner": "FHIR server / integration team",
        "remediation_timeline": "Weeks — meta.source population on all writes"
      }
    ]
  },
  "provenance_coverage": {
    "asserted": 0.11,
    "high": 0.34,
    "medium": 0.41,
    "low": 0.14,
    "unknown": 0.0
  },
  "feed_manifest_declared": true,
  "undeclared_sources": 0
}
```

---

## Technology Stack

### Client-side conformance testing kit (Stage 1, runs on plan infrastructure)

| Component | Rung 1–2 default | Rung 3+ upgrade | Notes |
|---|---|---|---|
| Bulk FHIR API conformance | stage1a_bulk_fhir_export_preflight (Python) | stage1a_bulk_fhir_export_preflight (same) | Live server test — no validator dependency |
| ndjson validator (Stage 1b) | stage1b_ndjson_validator (Python) | stage1b_ndjson_validator (same) | No external dependency |
| FHIR R4 structural conformance testing | HAPI Validator CLI | Aidbox native conformance testing | HAPI: no vendor contract needed |
| US Core 6.1.0 conformance | HAPI Validator CLI + US Core IG | Aidbox native validation | HAPI: runs anywhere Java available |
| Report output | JSON + PDF render | JSON + PDF render | Three reports per kit run |

**Validator backend is a deliberate ladder design decision.** HAPI is the default because it requires no Health Samurai contract, no HIPAA review, no procurement — the client runs it on their own infrastructure with no external dependencies beyond a Java runtime. When the plan advances to Rung 3 and has Aidbox in production, the conformance testing backend switches to Aidbox native conformance testing, which provides richer error metadata, write-time conformance testing rather than post-hoc, and consistent behaviour between the client kit and the sandbox. The reports are structurally identical regardless of backend — the findings format does not change.

### Sonian sandbox (Stages 3–5, runs on Sonian/Health Samurai infrastructure)

| Component | Technology | Version |
|---|---|---|
| FHIR server | Aidbox (Health Samurai) | Current |
| Terminology server | Termbox (Health Samurai) | Current |
| Database | PostgreSQL (Aidbox-managed) | 14+ |
| FHIR validation (sandbox) | Aidbox native + HAPI CLI | Latest |
| US Core IG | hl7.fhir.us.core | 6.1.0 |
| SQL on FHIR | SQL on FHIR v2 ViewDefinition | HL7 spec |
| Anonymization | Python 3.11+ | — |
| Lineage tooling | OpenLineage / Marquez (optional) | — |

---

## Open Items — Confirm Before Build

1. **NCQA dQM license for SQL query derivation** — confirm whether building SQL on FHIR queries from Vol. 2 narrative specifications (Sonian-held license) requires separate authorization for consulting use, or whether deriving queries from dQM CQL packages requires a custom NCQA license. Path 2 (Vol. 2 derivation) is the safe default.

2. **Aidbox US Core 6.1.0 profile validation on write** — confirm with Health Samurai that Aidbox supports US Core 6.1.0 profile validation at write time (not just at query time). Confirm whether auto-Provenance generation on ingest is configurable.

3. **Termbox standalone licensing** — confirm with Health Samurai whether Termbox can be licensed independently of Aidbox for plans that already have a FHIR server. This affects UC3 (monitoring service) commercial model.

4. **Velox Health Metadata integration** — confirm Velox's specific capabilities for feed-level lineage documentation. Velox is a clinical data inventory and scoring platform (veloxhealthmetadata.com). Their 10-10-10 assessment process is complementary to DQAR. Explore referral/partner relationship.

5. **NCQA dQM Evaluation Package pricing** — contact NCQA Account Executive to confirm pricing and whether evaluation package covers consulting use of JSON value sets.
