# DQAR Bulk FHIR Extract Specification
**Digital Quality Audit Readiness — Sonian**
*Version 2.0 | June 2026 | Confidential — For Client Use Only*
*mcampbell@indicina.com | Sonian.io*

---

## 1. Purpose and Scope

This document specifies the Bulk FHIR data extract Sonian requires from your organization to conduct a Digital Quality Audit Readiness (DQAR) assessment engagement. It defines which FHIR R4 resource types to export, the population scope and time window, the anonymization protocol required to protect member PHI, and the technical delivery format.

The extract supports semantic integrity assessment across use case domains depending on engagement scope:

| # | Use Case | Assessment Focus |
|---|---|---|
| UC1 | Digital Measure Readiness | HEDIS ECDS measure semantic conformance testing — five-level framework against MP2025 specifications |
| UC2 | Digital Quality Data Operations Monitoring | Continuous DQAR conformance monitoring — drift detection, VSD currency, governance maturity progression |
| UC3 | P2P Data Exchange Quality | Incoming payer-to-payer data semantic validity, completeness, and provenance assessment (CMS-0057-F) |

Sonian will confirm the specific use cases in scope at engagement kickoff. This document covers the superset — organizations may provide a subset of resources if only specific use cases are in scope.

---

## 2. Important Notes Before You Begin

> **🔒 PHI never enters Sonian's infrastructure.** All conformance testing (Stage 1a, 1b, 1c) executes within the client's own environment using Sonian-provided tooling. Only anonymized extracts and conformance reports cross the PHI boundary. No BAA is required for the assessment phase under this architecture.

> **⚠ The extract is used for gap identification and indicative rate calculation only.** SQL on FHIR queries produce diagnostic findings, not certified HEDIS rates. Your organization retains all reporting obligations under your NCQA license.

**Terminology — please use the following terms in communications with your IT team:**
- `Bulk FHIR export` or `Bulk FHIR data extract` — NOT 'FHIR packages' (different HL7 meaning)
- `$export operation` — the FHIR Bulk Data Access IG operation used to generate the extract
- `ndjson` — the output format (newline-delimited JSON, one resource per line per file)
- `US Core 6.1.0` — the required conformance target for all resources in this extract
- `anonymized extract` — PHI-stripped output per this specification's anonymization protocol

### 2.1 Required Conformance Standard — US Core 6.1.0

All resources in this extract must conform to the US Core Implementation Guide STU 6.1.0, which aligns with USCDI v3. This is the version required under CMS-0057-F (45 CFR 170.215) and approved by ONC for use in the Health IT Certification Program.

| US Core Version | USCDI Version | Regulatory Context | Status |
|---|---|---|---|
| US Core 3.1.1 | USCDI v1 | Original CMS-9115 (2021) | **OUTDATED — UC3 gap finding** |
| US Core 6.1.0 | USCDI v3 / v3.1 | CMS-0057-F required (2024) | **REQUIRED for this extract** |
| US Core 7.0.0 | USCDI v5 | ONC SVAP voluntary adoption | Acceptable — forward-compatible |

> **⚠** Plans on US Core 3.1.1 (original CMS-9115 implementation) should declare their version and provide their current extract. The version gap will be documented as a UC3 digital readiness finding with the Jan 1, 2027 CMS-0057-F compliance deadline attached. Sonian will assess against the available version and document the conformance delta.

### 2.2 Assessment Pipeline Architecture

The extract flows through a six-stage pipeline. Stage 1 (with substages 1a, 1b, 1c) executes entirely within the client environment against PHI-containing data. Stage 2 (PHI redaction) is optional and client-initiated. Stages 3–5 execute in the Sonian or plan-owned Aidbox environment.

**The three Stage 1 substages test independent dimensions and run in sequence:**
- **Stage 1a** tests the FHIR vendor server's `$export` API implementation against the Bulk Data Access IG — before any data moves.
- **Stage 1b** tests the ndjson structural integrity of the exported files — is each line parseable? Is `resourceType` present?
- **Stage 1c** tests US Core 6.1.0 profile conformance of the resource content — two sub-passes (base FHIR R4, then US Core IG).

A plan can fail Stage 1a while producing US Core-conformant resources. A plan can pass Stage 1a and 1b while every resource fails US Core profiles. These are answers to three completely different questions.

#### Pipeline stages

```
CLIENT ENVIRONMENT — PHI present. Stage 1 substages execute on client infrastructure.
Nothing leaves the client until Stage 2 (PHI redaction, optional) or direct Aidbox load (Path C).

Stage 1a  Bulk FHIR API conformance testing        [stage1a_bulk_fhir_export_preflight.py]
          Live conformance test of the plan's FHIR vendor server $export implementation
          against SMART Bulk Data Access IG STU2. Six checks: CapabilityStatement declares
          $export; kick-off returns 202 Accepted; Content-Location header present; polling
          completes with 200; manifest contains output[] and requiresAccessToken; output files
          return application/fhir+ndjson content-type.
          Skipped automatically if $export not declared in CapabilityStatement.
          Output: stage1a-{engagement}.json

Stage 1b  ndjson structural conformance testing     [stage1b_ndjson_validator.py]
          Validates every line of every ndjson file: parseable JSON; resourceType present;
          one resource per line; UTF-8 encoding; resourceType matches filename stem
          (e.g. Patient.ndjson must contain only Patient resources — mismatch indicates
          a mis-routed or mis-named file). FAIL at 1b blocks Stage 1c.
          Finding owner: FHIR server / infrastructure / DevOps team. DQAR Tier 3.
          Output: stage1b-{engagement}.json + PDF render

Stage 1c  FHIR R4 + US Core conformance testing    [stage1c_fhir_uscore_validator.py]
          Two sub-passes using HAPI Validator CLI (default) or Aidbox (Rung 3+ upgrade):
            1c-i  — Base FHIR R4 (4.0.1) structural conformance testing (no IG).
                    Finding owner: ETL / integration team. DQAR Tier 2.
            1c-ii — US Core 6.1.0 profile conformance testing.
                    Finding owner: clinical informatics + integration team. DQAR Tier 2.
          Output: stage1c-i-{engagement}.json + stage1c-ii-{engagement}.json

→ Client receives 3 JSON reports + 3 PDF renders.
→ Client decision point — three paths forward:

  PATH A — Stop here. No data leaves the plan.
            Act on findings using internal staff or Sonian advisory.

  PATH B — Stage 2 PHI redaction locally, then send anonymized extract to Sonian sandbox.
            No PHI crosses the boundary. Appropriate during HS HIPAA/SOC2 due diligence.

  PATH C — Full PHI loads directly to plan-owned Aidbox instance (post BAA).
            No anonymization step. Target state — platform ladder destination.

Stage 2   PHI redaction + anonymization             [PATH B ONLY — client-initiated]
          Anonymization protocol applied per Section 5. Referential integrity preserved.
          Pseudonym mapping table retained within client environment.
          Not required for Path A or Path C.

─────────────────── PHI BOUNDARY (Path B only) ────────────────────
Anonymized extract + Stage 1 reports cross to Sonian.
Path C bypasses this boundary entirely.

SONIAN / PLAN-OWNED AIDBOX ENVIRONMENT

Stage 3   Load to Aidbox sandbox (Path B) or plan-owned Aidbox (Path C)
          Each resource and its AuditEvent posted as single atomic transaction.
          (a) Re-run Stage 1b + 1c conformance testing on loaded extract
              → confirms redaction did not corrupt structural integrity
              → creates permanent conformance baseline for this extract
          (b) Termbox $validate-code — US Core required bindings + HEDIS MP2025 VSD
              (369 value sets). DQAR Tier 1 if governance process absent.
          (c) AuditEvent + seven extensions generated atomically per resource

Stage 4   DQAR SQL on FHIR assessment queries
          SQL on FHIR v2 ViewDefinitions execute against Aidbox / PostgreSQL.
          Five-level semantic conformance testing + Level 6 governance assessment.
          Measure attribution join queries link denominator flags to AuditEvent metadata.
          Risk stratification matrix generated automatically from AuditEvent metadata.

Stage 5   Three-tier findings report generation
          Tier 1 — Governance gaps (DAMA-BOK grounded)
          Tier 2 — Measure data gaps (affecting rates now)
          Tier 3 — Digital readiness gaps (MP2029 / CMS-0057-F)
          Each finding: technical severity + governance root cause +
          DAMA-DMBOK maturity score + remediation recommendation.
```

#### Finding tier and remediation owner — by pipeline stage

| Stage | Finding Type | DQAR Tier | Remediation Owner | Timeline |
|---|---|---|---|---|
| 1a | Bulk FHIR IG non-compliance — CapabilityStatement missing $export, manifest invalid | Tier 3 — Digital readiness gap | FHIR server / infrastructure / DevOps | Days to weeks |
| 1b | ndjson structural failure — unparseable JSON, missing resourceType, truncated files | Tier 3 — Digital readiness gap | FHIR server / infrastructure / DevOps | Days |
| 1c-i | Invalid FHIR R4 structure — bad data types, unknown resource types, malformed references | Tier 2 — Measure data gap | ETL / integration team | Weeks |
| 1c-ii | US Core 6.1.0 profile failure — missing MUST SUPPORT elements, invalid required bindings | Tier 2 — Measure data gap | Clinical informatics + integration team | Weeks to months |
| 3 (Termbox) | Terminology conformance failure — code not in required value set, stale VSD binding. Governance absence also a Tier 1 finding. | Tier 1/2 — Governance or measure data gap | Terminology governance function | Depends on governance maturity |
| 4 (SQL on FHIR) | Semantic context failure — wrong encounter type, measurement window violation, exclusion misapplication | Tier 2 — Measure data gap | Clinical informatics — measure logic implementation | Weeks per measure |

> **⚠ Why Stage 1 substages run in the client environment:** US Core 6.1.0 MUST SUPPORT elements include PHI-bearing fields (Patient.name, Patient.birthDate). Running conformance testing after redaction cannot distinguish 'field absent in client data' from 'field redacted by protocol' — findings would misrepresent the client's actual data quality. Running conformance testing in the client environment resolves this without requiring Sonian to handle PHI.

### 2.3 Conformance Testing Backend — HAPI vs Aidbox

Stage 1c supports two conformance testing backends selected via the `--backend` flag. The choice depends on the plan's platform ladder rung:

| `--backend` | When Used | Notes |
|---|---|---|
| `hapi-cli` (default) | Rung 1 and Rung 2. No Aidbox contract required. | HAPI Validator CLI JAR. Runs anywhere Java is available. Set `FHIR_VALIDATOR_JAR` env var or pass `--validator-jar`. Reports structurally identical to Aidbox output. |
| `aidbox` | Rung 3+ — when plan has Aidbox in production. | Aidbox `$validate` REST API. `--engagement` must be a path to an engagement config JSON (`config/engagements/`). Issues classified into 1c-i / 1c-ii by US Core profile URL in OperationOutcome diagnostics. Consistent behaviour between client kit and sandbox. |

```bash
# Rung 1/2 — HAPI CLI (default)
python stage1c_fhir_uscore_validator.py \
  --ndjson-dir data/export --engagement client-name --backend hapi-cli

# Rung 3+ — Aidbox $validate REST API
python stage1c_fhir_uscore_validator.py \
  --ndjson-dir data/export --engagement config/engagements/client.json --backend aidbox
```

Both backends produce the same two output files and the same report schema. `"validator_version"` is present only for `hapi-cli`.

---

## 3. AuditEvent Extension Metadata — Generated at Stage 3

AuditEvent resources in the DQAR assessment sandbox are generated by the Sonian ingestion pipeline at Stage 3 when each resource is loaded to Aidbox. Each AuditEvent is posted atomically with its associated clinical resource as a FHIR transaction bundle.

The pipeline attaches **seven extension fields** to every AuditEvent it generates. Four fields are populated by the source-type inference algorithm (`dqar-05-source-inference-algorithm.md`). One field (`ingest-pipeline-id`) is set by the pipeline orchestrator. One field (`ecds-ssor`) is derived from `source-type` via deterministic SSoR mapping rule. One field (`ol-run-id`) is the OpenLineage run ID that links the AuditEvent to the lineage graph.

### 3.1 Extension Definitions

| Extension URL | valueType | Example Value | Purpose / DQAR Use |
|---|---|---|---|
| `http://Sonian.io/fhir/ext/source-type` (EXT 1) | valueCode | `clinical_ehr` | Expanded 13-value vocabulary. **Tier A** (structurally detectable): `clinical_ehr`, `administrative_claims`, `administrative_encounter`, `pharmacy_pbm`, `clinical_lab`, `payer_exchange`, `clinical_immunization_registry`. **Tier B** (manifest/meta.source only): `clinical_phr`, `pharmacy_specialty`, `clinical_hie`, `clinical_registry`, `case_management`, `disease_management`. Tier B resources defaulting to `unknown` are Tier 1 governance findings. |
| `http://Sonian.io/fhir/ext/source-system-id` (EXT 2) | valueString | `epic-prod-org-447` | Pseudonymized identifier of the specific source system instance. Consistent across all resources from same source. Enables Study Type 1 and 2 lineage tracing. |
| `http://Sonian.io/fhir/ext/source-feed-id` (EXT 3) | valueString | `epic-prod-org-447` | Feed-level identifier independent of full pipeline composite. Primary key for feed-level findings queries and risk stratification matrix. |
| `http://Sonian.io/fhir/ext/source-inference-confidence` (EXT 4) | valueCode | `asserted` | Confidence tier: `asserted` \| `high` \| `medium` \| `low` \| `unknown`. Confidence distribution across the extract is a direct provenance maturity metric and Tier 1 governance finding driver. |
| `http://Sonian.io/fhir/ext/ecds-ssor` (EXT 5) | valueCode | `EHR/PHR` | NCQA ECDS Source of Record (SSoR) category. Four-value vocabulary: `EHR/PHR` \| `Administrative` \| `Clinical Registry/HIE` \| `Case/Disease Mgmt`. Derived from source-type via deterministic SSoR mapping rule. `null` when source-type = `unknown` — triggers Tier 1 governance finding. |
| `http://Sonian.io/fhir/ext/ingest-pipeline-id` (EXT 6) | valueString | `dqar-20251014-001/epic-prod-org447/Condition.ndjson-chunk-003` | Three-level traceability: run / feed / batch. Enables batch-level error isolation without full re-scan. |
| `http://Sonian.io/fhir/ext/ol-run-id` (EXT 7) | valueString | `550e8400-e29b-41d4-a716-446655440000` | Ingest batch tag (UUID v4) stamped on every AuditEvent written during a run — not a join key into a lineage graph. OpenLineage RunEvents are emitted directly to OpenMetadata (Marquez has been dropped); OpenMetadata builds the lineage graph from each RunEvent's declared inputs/outputs. Required for DQAR provenance maturity Level 3+. |

### 3.2 Source-Type to SSoR Mapping

| source-type (EXT 1) | ECDS SSoR (EXT 5) |
|---|---|
| `clinical_ehr` | EHR/PHR |
| `clinical_phr` | EHR/PHR |
| `payer_exchange` | EHR/PHR |
| `administrative_claims` | Administrative |
| `administrative_encounter` | Administrative |
| `pharmacy_pbm` | Administrative |
| `pharmacy_specialty` | Administrative |
| `clinical_lab` | Clinical Registry/HIE |
| `clinical_hie` | Clinical Registry/HIE |
| `clinical_registry` | Clinical Registry/HIE |
| `clinical_immunization_registry` | Clinical Registry/HIE |
| `case_management` | Case/Disease Mgmt |
| `disease_management` | Case/Disease Mgmt |
| `unknown` | None → Tier 1 governance finding |

### 3.3 AuditEvent Example — Seven Extensions

```json
{
  "resourceType": "AuditEvent",
  "recorded": "2025-10-14T09:22:00Z",
  "agent": [{ "requestor": true, "who": { "display": "dqar-ingest-pipeline" } }],
  "source": { "observer": { "display": "Sonian DQAR Sandbox" } },
  "entity": [{ "what": { "reference": "Condition/pat-abc123-cond-001" } }],
  "extension": [
    { "url": "http://Sonian.io/fhir/ext/source-type",
      "valueCode": "clinical_ehr" },                                    // EXT 1
    { "url": "http://Sonian.io/fhir/ext/source-system-id",
      "valueString": "epic-prod-org-447" },                             // EXT 2
    { "url": "http://Sonian.io/fhir/ext/source-feed-id",
      "valueString": "epic-prod-org-447" },                             // EXT 3
    { "url": "http://Sonian.io/fhir/ext/source-inference-confidence",
      "valueCode": "asserted" },                                        // EXT 4
    { "url": "http://Sonian.io/fhir/ext/ecds-ssor",
      "valueCode": "EHR/PHR" },                                         // EXT 5
    { "url": "http://Sonian.io/fhir/ext/ingest-pipeline-id",
      "valueString": "dqar-20251014-001/epic-prod-org447/Condition.ndjson-chunk-003" }, // EXT 6
    { "url": "http://Sonian.io/fhir/ext/ol-run-id",
      "valueString": "550e8400-e29b-41d4-a716-446655440000" }           // EXT 7
  ]
}
```

> EXT 5 (`ecds-ssor`) uses the four-category NCQA SSoR vocabulary and is derived from EXT 1 (`source-type`) via deterministic mapping rule. SSoR = `null` when `source-type = unknown`, which triggers a Tier 1 governance finding on metadata management maturity. EXT 6 (`ingest-pipeline-id`) and EXT 7 (`ol-run-id`) are both set by the pipeline orchestrator at ingest time; EXT 7 is an ingest batch tag, not a join key — OpenLineage RunEvents go directly to OpenMetadata (Marquez dropped), which builds the lineage graph from each RunEvent's declared inputs/outputs.

---

## 4. Resource Type Specification

### 4.1 Mandatory Core — All Use Cases

These resource types are required for every DQAR engagement regardless of use case scope.

| Resource Type | FHIR R4 Resource | Use Cases | Status | Key Fields / Notes |
|---|---|---|---|---|
| Patient | Patient | All | **REQUIRED** | Pseudonymize: id, identifier, name, address, telecom, birthDate (keep year only). Keep: gender, language, deceased flag, race/ethnicity extensions |
| Coverage | Coverage | All | **REQUIRED** | Pseudonymize: memberId, subscriberId. Keep: period, payor ref, class (product line), relationship |
| Organization | Organization | All | **REQUIRED** | Pseudonymize: name → org-{hash}. Keep: type, address (city/state/zip only), identifier (NPI) |
| Practitioner | Practitioner | All | **REQUIRED** | Pseudonymize: name → prac-{hash}. Keep: identifier (NPI), qualification, gender |
| PractitionerRole | PractitionerRole | All | **REQUIRED** | No direct PHI. Keep: practitioner ref, organization ref, specialty, location ref |
| Location | Location | All | **REQUIRED** | Pseudonymize: name, address (keep city/state/zip). Keep: type, physicalType, managingOrganization |

### 4.2 Clinical Layer — HEDIS dQM / ECDS (UC1, UC2)

Required for Level 1–5 semantic conformance testing against HEDIS MP2025 measure specifications.

| Resource Type | FHIR R4 Resource | Use Cases | Status | Key Fields / Notes |
|---|---|---|---|---|
| Condition | Condition | UC1, UC2 | **REQUIRED** | Keep: code (ICD-10-CM + SNOMED), clinicalStatus, verificationStatus, onset, recorder, subject ref, encounter ref |
| Observation | Observation | UC1, UC2 | **REQUIRED** | Keep: status, category (MUST SUPPORT), code (LOINC), value[x], effectiveDateTime, subject ref, encounter ref |
| Encounter | Encounter | UC1, UC2 | **REQUIRED** | Keep: status, class, type (CPT/SNOMED), period, participant, location ref, serviceProvider ref |
| Procedure | Procedure | UC1, UC2 | **REQUIRED** | Keep: status, code (CPT/SNOMED/ICD-10-PCS), performed[x], performer, subject ref, encounter ref |
| MedicationRequest | MedicationRequest | UC1, UC2 | **REQUIRED** | Keep: status, medication[x] (RxNorm), authoredOn, dosageInstruction (MUST SUPPORT in 6.1.0), subject ref |
| MedicationDispense | MedicationDispense | UC1, UC2 | **REQUIRED** | Keep: status, medication[x] (RxNorm/NDC), quantity, whenHandedOver, subject ref |
| Immunization | Immunization | UC1, UC2 | **REQUIRED** | Keep: status, vaccineCode (CVX), occurrenceDateTime, patient ref |
| DiagnosticReport | DiagnosticReport | UC1, UC2 | **REQUIRED** | Keep: status, category, code (LOINC), effective[x], result refs. Remove: presentedForm (base64) |
| ServiceRequest | ServiceRequest | UC1, UC2 | RECOMMENDED | Referral orders — relevant to FUH/FUM, BCS-E |
| Goal | Goal | UC1, UC2 | RECOMMENDED | Care plan goals for chronic condition measures |

### 4.3 Administrative Layer — Claims / Pharmacy

| Resource Type | FHIR R4 Resource | Use Cases | Status | Key Fields / Notes |
|---|---|---|---|---|
| ExplanationOfBenefit | ExplanationOfBenefit | UC1, UC2, UC3 | **REQUIRED** | CARIN Blue Button IG STU 2.0.0/2.1.0 format for UC3. Keep: status, type, billablePeriod, provider ref, diagnosis, procedure, item. Remove: unitPrice, adjudication amounts |
| Claim | Claim | UC1, UC2 | RECOMMENDED | Keep: status, type, billablePeriod, diagnosis, procedure, item. Remove: financial fields |

### 4.4 Provenance and Lineage

| Resource Type | FHIR R4 Resource | Use Cases | Status | Key Fields / Notes |
|---|---|---|---|---|
| AuditEvent | AuditEvent | All | **REQUIRED (may be empty)** | Client AuditEvents from FHIR server included even if empty — absence is a scored Tier 3 finding. Sonian generates its own AuditEvents with seven extensions at Stage 3. |
| Provenance | Provenance | All | RECOMMENDED | Include via `includeAssociatedData=hl7.fhir.uv.bulkdata#Provenance` if supported. Absence documented as Tier 3 finding. PDex Provenance is a positive finding if present for UC3. |

---

## 5. Anonymization Protocol

### 5.1 PHI Redaction Requirements

PHI redaction is required for **Path B only**. Path C (plan-owned Aidbox, post BAA) does not require redaction. All redaction occurs within the client environment before any data crosses the PHI boundary.

| Field | Risk Level | Action | Notes |
|---|---|---|---|
| Patient.id | CRITICAL | Replace with pat-{SHA256[:8]} | Consistent pseudonym used as join key across all resource references |
| Patient.identifier | CRITICAL | Remove all — member ID, MRN, SSN | Identifiers not required for conformance testing or measure calculation |
| Patient.name | CRITICAL | Remove entirely | Name not used in any DQAR assessment query |
| Patient.birthDate | HIGH | Retain year only — e.g. 1972 | Age required for age-stratified measures |
| Patient.address | HIGH | Retain zip code only (5-digit) | Geographic stratification may be relevant |
| Patient.telecom | HIGH | Remove entirely | Phone/email not required |
| Practitioner.name | HIGH | Replace with prac-{hash[:8]} | NPI retained for provider attribution |
| Organization.name | MEDIUM | Replace with org-{hash[:8]} | Organization type and NPI retained |
| Observation.valueString (free text) | HIGH | Remove entirely | Coded values retained |
| DiagnosticReport.presentedForm | HIGH | Remove entirely (base64) | Coded fields in referenced Observations sufficient |
| AuditEvent.agent.name | MEDIUM | Replace with agent-{hash[:8]} | Agent type and requestor flag retained |
| ExplanationOfBenefit financial fields | MEDIUM | Remove or zero out | Payment amounts not required |

### 5.2 Referential Integrity Requirement

Referential integrity must be preserved across all resource references after anonymization. If `Patient.id` is pseudonymized to `pat-abc123`, then every `Condition.subject`, `Observation.subject`, `Encounter.subject`, `Coverage.beneficiary`, and `AuditEvent.entity` reference pointing to that patient must use `pat-abc123`.

> **⚠** Broken referential integrity is the most common anonymization failure mode and renders the extract partially or fully unusable for Level 3 context conformance testing. Sonian recommends testing a 50-member sample for referential integrity before delivering the full extract.

---

## 6. Delivery Format and Checklist

### 6.1 File Format

- Format: ndjson (newline-delimited JSON), one FHIR resource per line
- File naming: one file per resource type — `Patient.ndjson`, `Coverage.ndjson`, `Condition.ndjson`, etc.
- Encoding: UTF-8
- Compression: gzip compression accepted (`.ndjson.gz`)
- Delivery: encrypted file transfer via SFTP or secure cloud storage link provided by Sonian at engagement kickoff

### 6.2 Delivery Checklist

| # | Checklist Item | Status |
|---|---|---|
| 1 | US Core version declared — state which version your FHIR server implements (3.1.1 / 6.1.0 / 7.0.0) in Section 6.3 | ☐ Confirmed |
| 2 | CapabilityStatement reviewed — confirm which resource types your server supports in `$export` before generating extract | ☐ Confirmed |
| 3 | Stage 1a Bulk FHIR API conformance completed — `stage1a_bulk_fhir_export_preflight.py` run against FHIR vendor server before export | ☐ Confirmed |
| 4 | Stage 1b ndjson conformance testing completed — `stage1b_ndjson_validator.py` run against raw extract before redaction | ☐ Confirmed |
| 5 | Stage 1c FHIR R4 + US Core conformance testing completed — `stage1c_fhir_uscore_validator.py` (HAPI or Aidbox) run against raw extract | ☐ Confirmed |
| 6 | Anonymization protocol applied per Section 5 (Path B only — not required for Path C) | ☐ Confirmed |
| 7 | Referential integrity verified on a 50-member test sample — all cross-references use consistent pseudonyms | ☐ Confirmed |
| 8 | All mandatory core resources present (Patient, Coverage, Organization, Practitioner, PractitionerRole, Location) | ☐ Confirmed |
| 9 | Clinical resources present for at least 3 of the 5 priority measures (CBP, CDC, COL-E, BCS-E, FUH/FUM) | ☐ Confirmed |
| 10 | Time window covers minimum 24 months of clinical history | ☐ Confirmed |
| 11 | Population stratification includes all product lines | ☐ Confirmed |
| 12 | Provenance resources included via `includeAssociatedData` parameter or noted as absent in Section 6.3 | ☐ Confirmed |
| 13 | AuditEvent file included (even if empty — note gap in Section 6.3; absence is a scored finding) | ☐ Confirmed |
| 14 | File naming follows `resource-type.ndjson` convention | ☐ Confirmed |
| 15 | Delivery via Sonian-provided secure channel | ☐ Confirmed |

### 6.3 Known Gaps — Please Document

If your organization cannot produce certain resource types or must deviate from the anonymization protocol, document those gaps here before delivery. Known gaps are scored differently from undocumented gaps in the DQAR findings report — documentation demonstrates governance awareness.

| Resource / Element | Gap Description | Reason / Context |
|---|---|---|
| | | |
| | | |
| | | |

---

## 7. Questions and Support

For questions about this specification, contact:

**Michael E. Campbell**
Healthcare Informatics Strategist and Consultant
Sonian
mcampbell@indicina.com

For technical questions about the `$export` operation or FHIR Bulk Data Access IG: https://hl7.org/fhir/uv/bulkdata/

For questions about CARIN Blue Button IG (ExplanationOfBenefit profile): https://hl7.org/fhir/us/carin-bb/

*Sonian will acknowledge receipt of the extract within one business day and confirm readiness to begin the assessment phase. Questions about individual resource type availability or anonymization approach are welcome prior to export — it is preferable to resolve ambiguities before generating a large extract than to discover issues after delivery.*

---

## Change Log — v1.0 to v2.0

| Area | v1.0 | v2.0 |
|---|---|---|
| Document name | Digital Quality Audit **Framework** (DQAF) | Digital Quality Audit **Readiness** (DQAR) |
| Stage numbering | Stage 1, 2a, 2b-i, 2b-ii, 3, 4, 5, 6 | Stage 1a, 1b, 1c (client); Stage 2–5 (pipeline) |
| Stage 1a | Not present | New — Bulk FHIR API conformance preflight (`stage1a_bulk_fhir_export_preflight.py`) |
| Stage 1b | Was Stage 2a | ndjson structural conformance testing |
| Stage 1c | Was Stage 2b-i + 2b-ii | FHIR R4 + US Core conformance testing (sub-passes 1c-i, 1c-ii) |
| Stage 2 | Was Stage 3 | PHI redaction (Path B only) |
| Stage 3 | Was Stage 5 | Aidbox load |
| Client paths | Not explicit | Path A (stop), Path B (anonymized sandbox), Path C (full PHI, plan-owned Aidbox) |
| AuditEvent extensions | 4 extensions | 7 extensions |
| EXT 1 source-type vocabulary | 5 values: ehr-clinical, administrative, lab, pharmacy, p2p | 13 values with Tier A/B detectability framework |
| EXT 3 source-feed-id | Informal | Formal — primary key for feed-level queries |
| EXT 4 source-inference-confidence | Informal | Formal — direct provenance maturity metric |
| EXT 5 ecds-ssor | Not present | **New** — four-category NCQA SSoR vocabulary |
| EXT 6 ingest-pipeline-id | Informal | Formal — orchestrator-set; three-level run/feed/batch traceability |
| EXT 7 ol-run-id | Not present | **New** — OpenLineage run ID UUID; ingest batch tag (not a join key); RunEvents go directly to OpenMetadata; required for Level 3+ maturity |
| SSoR mapping table | Not present | Full 12-type → SSoR mapping rule |
| Tier 1 finding name | Compliance gap | Governance gap (DAMA-BOK grounded) |
| Measurement year | MY2025 | MP2025 (measurement period) |
| UC2 name | Pre-Audit Preparation | Digital Quality Data Operations Monitoring |
| Section 2.3 | Not present | New — HAPI vs Aidbox backend ladder design |
| Conformance testing language | "validation" throughout Stage 1 context | "conformance testing" (Stage 1) vs "validation" (semantic Levels 3–5) |
