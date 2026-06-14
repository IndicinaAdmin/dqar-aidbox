# Risk-Stratified Data Lineage Studies
**DQAR Domain 3 — Data Lineage Tracing**
*Version: June 2026 | Confidential — Internal Reference*

---

## Overview

A risk-stratified data lineage study is the DQAR analog to PSV medical record sampling — applied to data pipelines rather than charts. Instead of reviewing every pipeline hop for every member, the assessment identifies the highest-risk lineage paths in the plan's data inventory and draws a structured sample from each.

The procedure produces five to seven studies per assessment engagement. Each study is selected because it represents a distinct lineage failure mode category with material rate impact if broken. Together they provide population-scale confidence that the plan's data pipeline is traceable, governed, and producing measure-defensible output.

**Why five to seven:** Fewer than five understates the complexity of a modern payer stack (which typically has five or more distinct source system types feeding HEDIS). More than seven produces diminishing diagnostic returns within a fixed-fee engagement scope. The number scales with plan size and pipeline complexity — a 500K-member plan with a single claims system warrants fewer studies than a 5M-member plan with five upstream vendors.

---

## Step 1 — Data Inventory and Lineage Graph Construction

Before selecting studies, you must map the plan's complete HEDIS data inventory. This is the prerequisite that the NCQA IS Assessment nominally covers but in practice collects as narrative descriptions and staff interviews. DQAR requires a machine-readable inventory — a more rigorous and technically defensible standard.

**Inventory elements per source system:**

| Element | Description | Collection method |
|---|---|---|
| Source system ID | Canonical identifier (e.g., "epic-prod-org-447") | System documentation |
| Source system type | EHR / claims / lab / pharmacy / HIE / SDoH / P2P | Interview + confirmation |
| Data elements contributed | Which FHIR resource types and fields | Schema documentation |
| HEDIS measures affected | Which denominators/numerators this source feeds | Measure specification mapping |
| Transformation hops | ETL/ELT steps between source and FHIR server | Pipeline documentation |
| Lineage tool coverage | Is this path covered by dbt/OpenLineage/Velox or undocumented? | Technical assessment |
| Last validated | When was this path last tested end-to-end? | Change log review |

**Lineage graph construction:**

If the plan has OpenLineage, Velox, dbt lineage, or equivalent — extract the lineage graph directly. This is the ideal case: the graph exists, Indicina queries it, the inventory is machine-readable.

If no lineage tool exists — construct the inventory manually from system documentation, ETL code review, and staff interviews. Document the absence of lineage tooling as a Level 6 governance finding (metadata management maturity = 1).

The lineage graph topology for a typical payer HEDIS pipeline:

```
CAPS (claims adjudication)
    → 837 inbound processing → EDW claims tables
        → ETL/dbt transformation → FHIR Claim/ExplanationOfBenefit
            → Aidbox FHIR server
                → CQL/SQL on FHIR measure execution
                    → HEDIS MeasureReport

EHR vendor feeds (HL7v2 / C-CDA)
    → Interbox/integration engine → FHIR Condition/Observation/Encounter
        → Aidbox FHIR server
            → CQL/SQL on FHIR measure execution

Lab vendor feeds
    → HL7v2 ORU → FHIR Observation (laboratory)
        → Aidbox FHIR server
            → CQL/SQL on FHIR measure execution

Pharmacy PBM
    → NCPDP D.0 → FHIR MedicationDispense/MedicationRequest
        → Aidbox FHIR server
            → CQL/SQL on FHIR measure execution

P2P received data (CMS-0057-F)
    → FHIR Bundle (external payer)
        → Aidbox FHIR server
            → CQL/SQL on FHIR measure execution
```

Each arrow is a lineage hop. Each hop is a potential failure point.

---

## Step 2 — Risk Stratification

Once the inventory is complete, score each lineage path on two dimensions to prioritize which paths warrant a formal study:

**Risk dimension 1 — Measure rate impact**
How many HEDIS measures does this path feed? How many members' denominator or numerator status depends on data from this path? A path feeding 12 measures for 40% of the eligible population has higher rate impact than a path feeding 2 measures for 5%.

**The Aidbox ingest solution makes this dimension machine-computable, not manual.** The AuditEvent seven-extension pattern assigns `source-system-id`, `source-type`, `ecds-ssor`, and `ol-run-id` metadata to every resource at ingest time. This means the risk stratification query is a SQL on FHIR join — not a staff interview or documentation review. At the close of Stage 3 (Aidbox load), the assessment sandbox can immediately answer:

```sql
-- Per source-system-id: how many resources, which resource types,
-- which HEDIS measures they feed, and what % of the eligible population they touch
SELECT
  ae_ext_sys.value->>'valueString'   AS source_system_id,
  ae_ext_src.value->>'valueCode'     AS source_type,
  ae_ext_ssor.value->>'valueCode'    AS ecds_ssor,
  r.resource_type,
  COUNT(*)                           AS resource_count
FROM auditEvent ae
  CROSS JOIN LATERAL jsonb_array_elements(ae.resource->'extension') ae_ext_sys
  CROSS JOIN LATERAL jsonb_array_elements(ae.resource->'extension') ae_ext_src
  CROSS JOIN LATERAL jsonb_array_elements(ae.resource->'extension') ae_ext_ssor
WHERE ae_ext_sys.value->>'url'  = 'http://indicina.com/fhir/ext/source-system-id'
  AND ae_ext_src.value->>'url'  = 'http://indicina.com/fhir/ext/source-type'
  AND ae_ext_ssor.value->>'url' = 'http://indicina.com/fhir/ext/ecds-ssor'
GROUP BY 1, 2, 3, 4
ORDER BY resource_count DESC;
```

This query produces the risk stratification matrix automatically from the ingest metadata. Plans with no AuditEvent metadata must reconstruct this manually from ETL documentation — expensive, error-prone, and a Level 6 governance finding in its own right. The Aidbox solution converts a multi-day manual exercise into a sub-minute query. This is a direct, concrete demonstration of the value of the Indicina/Health Samurai infrastructure over an incumbent HEDIS vendor that does not expose this metadata to the plan.

**Risk dimension 2 — Lineage confidence**
How well-documented and validated is this path? A path with full dbt lineage, automated testing, and recent validation has high confidence. A path that is undocumented, manually maintained, or last validated two years ago has low confidence.

Plot each path on a 2×2:

```
                HIGH rate impact
                      |
    Quadrant B        |    Quadrant A  ← PRIORITY STUDIES
  (monitor closely)   |   (immediate study)
                      |
LOW lineage ──────────┼────────────── HIGH lineage
confidence            |               confidence
                      |
    Quadrant D        |    Quadrant C
   (low priority)     |  (verify only)
                      |
                LOW rate impact
```

**Quadrant A** — high rate impact, low lineage confidence: **mandatory study**. These are the paths most likely to be producing wrong measure rates with no audit trail.

**Quadrant B** — high rate impact, high lineage confidence: **targeted study**. High stakes justify verification even with documented lineage.

**Quadrant C** — low rate impact, high lineage confidence: **light review** only — confirm documentation is current.

**Quadrant D** — low rate impact, low lineage confidence: **document gap** as Level 6 finding but deprioritize for deep study within engagement scope.

---

## Step 3 — The Five Standard Study Types

Each formal lineage study follows a standard structure: select a sample, trace the lineage end-to-end, document findings, classify the failure mode if any. The five standard study types map to the most common payer pipeline failure patterns:

---

### Study Type 1 — Claims-to-FHIR Transformation Integrity

**What it tests:** Whether the transformation from raw claims (837/EDI) through the EDW to FHIR ExplanationOfBenefit or Claim resources preserves the clinical meaning required for HEDIS administrative data denominators.

**Sample selection:** Select 50–100 members from the denominator of a high-volume administrative measure (e.g., CBP, CDC). For each member, pull the raw claim record from the source system and the corresponding FHIR resource from the FHIR server. Trace every field through every transformation hop.

**Key failure modes to test:**
- Diagnosis code truncation or mapping errors (ICD-10 → FHIR Condition code)
- Encounter date shifting during transformation (admission date vs. service date vs. discharge date)
- Procedure code loss in multi-line claim aggregation
- Provider NPI mapping failures (billing NPI vs. rendering NPI)
- Service type code transformation (place of service → FHIR encounter class)

**Evidence produced:** Field-level transformation map for the sampled records. Pass/fail per field. Failure mode classification. Estimated population-level rate impact of any failures.

**Velox/OpenLineage role:** If the plan uses Velox or OpenLineage, the lineage graph for this path should already document the transformation rules. The study *verifies* that the documented rules match the actual data output — a critical distinction. Documented rules that don't match actual behavior are a Level 6 governance finding (change control failure).

---

### Study Type 2 — EHR Clinical Data Feed Completeness and Fidelity

**What it tests:** Whether EHR-sourced clinical data (diagnoses, observations, encounters) arriving via HL7v2 or C-CDA feeds is complete, correctly transformed to FHIR, and semantically valid for HEDIS ECDS measure denominators and numerators.

**Sample selection:** Select the five highest-volume EHR source systems by member count. For each, pull a sample of 20–30 members with qualifying clinical events (e.g., HbA1c results for CDC, blood pressure readings for CBP). Trace from EHR source record to FHIR Observation/Condition resource in the FHIR server.

**Key failure modes to test:**
- HL7v2 segment mapping errors (OBX → FHIR Observation field mapping)
- LOINC code assignment — is the correct LOINC being applied for this test in this EHR's local coding scheme?
- Result value transformation — unit conversion, numeric precision, reference range preservation
- Encounter linkage — is the Observation correctly linked to the Encounter that generated it?
- AuditEvent provenance — does the resource have the `ecds-ssor: EHR/PHR` extension (EXT 6) and a valid `ol-run-id` (EXT 7) that resolves in the OpenLineage graph?

**Evidence produced:** Source-to-FHIR field mapping for sampled records. LOINC assignment accuracy by EHR source. Encounter linkage completeness rate. Provenance coverage rate.

**Velox/OpenLineage role:** Velox is particularly relevant here — HL7v2 feeds are the primary gap in most payer lineage graphs. The feed arrives, gets transformed by the integration engine, and lands in the FHIR server, but the transformation mapping is rarely documented in a queryable lineage graph. Velox as the integration pipeline lineage tool closes this gap.

---

### Study Type 3 — Value Set Binding at Execution Point

**What it tests:** Whether the value set bindings being applied at measure execution (by the CQL engine or SQL on FHIR queries) match the authoritative NCQA MP2025 VSD — not just whether the codes exist in the value set (Level 1) but whether the value set version being used in production is current and correctly bound to the measure.

**Sample selection:** Select five measures with the highest historical rate volatility (rates that changed unexpectedly between MY2023 and MP2024). For each, pull the production value set binding — the actual list of codes being used in the denominator/numerator logic — and compare against the NCQA MP2025 VSD.

**Key failure modes to test:**
- Stale value set — production binding is a prior year VSD version
- Partial binding — production binding is a subset of the full value set (missing codes)
- Retired code inclusion — production binding includes codes retired in MP2025
- New code exclusion — production binding missing new codes added in MP2025
- Version mismatch across measures — same code system bound differently in two measures that share value sets

**Evidence produced:** Value set diff report per measure — additions, deletions, and retirements between production binding and MP2025 VSD. Estimated member count affected by each discrepancy. Rate impact estimate.

**Velox/OpenLineage role:** Value set bindings at execution are typically not captured in standard lineage graphs — they're embedded in CQL library references or SQL query parameters. Document whether the plan's lineage tooling captures binding version as metadata on measure execution runs. If not, that's a lineage coverage gap finding.

---

### Study Type 4 — Exclusion Code Application and Member Suppression

**What it tests:** Whether exclusion codes (medical reason, patient refusal, system exclusions) are being applied correctly and are not inadvertently suppressing eligible members from numerators.

**Sample selection:** For each measure with exclusion criteria, select a random sample of 30–50 members who were *excluded* from the numerator. Trace the exclusion code back to its source record and verify that the exclusion is clinically appropriate and correctly applied per the HEDIS specification.

**Key failure modes to test:**
- Exclusion code applied without a corresponding clinical event (phantom exclusion)
- Exclusion code in the wrong encounter type context
- Exclusion code applied outside the valid measurement window
- Medical reason exclusion applied where only patient refusal was documented
- Bulk exclusion application — a large number of members excluded by the same code on the same date, suggesting a batch processing artifact rather than individual clinical decisions

**Evidence produced:** Exclusion audit report per measure. Confirmed appropriate vs. potentially inappropriate exclusions. Population-level exclusion rate by code — anomalous concentrations flagged.

**Level 5 connection:** Bulk exclusion application is a Level 5 (population-level coherence) signal detectable by anomaly detection before the individual member trace confirms it. The lineage study and the Level 5 anomaly detection should be run together for exclusion analysis.

---

### Study Type 5 — Multi-Vendor Chain Integrity

**What it tests:** In plans using HIE aggregators, third-party abstraction vendors, or data analytics subcontractors, whether the vendor hand-off points in the pipeline preserve data integrity, provenance, and measure-eligibility semantics.

**Sample selection:** Identify every vendor in the HEDIS data chain beyond the plan's own systems. For each vendor, select a sample of 20–30 members whose clinical data flowed through that vendor. Trace from the vendor's output back to the original source record.

**Key failure modes to test:**
- Provenance loss at vendor boundary — data arrives from vendor without source attribution
- Schema normalization artifacts — vendor normalizes clinical data to a proprietary schema before delivering to the plan, losing context in the process
- Date normalization errors — vendor converts encounter dates to a different timezone or precision
- Filtering artifacts — vendor applies its own quality filtering before delivering data, silently excluding records the plan would have included
- Change control gap — vendor updated their transformation logic without notifying the plan, violating the documented control procedures

**Evidence produced:** Vendor chain documentation for each hand-off point. Pass/fail per provenance test. Change control evidence review. Estimated member count affected by any vendor-introduced artifacts.

**DQAR vs NCQA IS Assessment:** The NCQA IS Assessment asks for vendor agreements and documented control procedures. The DQAR lineage study tests whether those documented controls are actually producing correct output — a materially higher standard than confirming the documentation exists.

---

### Optional Study Type 6 — P2P Received Data Integrity

**Relevant for UC5 only.** Tests whether data received via Payer-to-Payer API exchange retains provenance, semantic validity, and completeness when processed by the receiving plan's ingest pipeline.

**Sample selection:** Select 30–50 members who transferred from another plan and whose clinical data was received via P2P exchange. Trace the received data from the P2P API response through the ingest pipeline to the FHIR server.

**Key failure modes to test:**
- Provenance loss — received resources lack source payer attribution
- Value set misalignment — clinical codes from the sending payer use a different value set version than the receiving plan's HEDIS pipeline expects
- FHIR profile mismatch — received resources conform to a different US Core version than the receiving plan's server expects
- Completeness gaps — expected clinical history is absent or truncated in the received data
- Duplicate resource creation — received resources create duplicates with existing administrative records for the same member

---

## Step 4 — Sampling Methodology

For each study, sample selection follows a consistent protocol to ensure findings are statistically defensible:

**Minimum sample size:** 30 members per study for plans under 1M members; 50 members for plans 1M–5M; 100 members for plans over 5M. This is analytically defensible and more rigorous than the NCQA IS Assessment sampling approach, which does not specify minimum sample sizes for lineage studies.

**Stratification:** Samples are stratified by source system where multiple sources feed the same measure. If CBP denominator is fed by three EHR systems and one claims system, the sample includes representation from all four.

**Random selection with purposive oversampling:** Base sample is random. Oversample (up to 20% of total) is purposive — members selected because they are at the intersection of known risk factors (e.g., members enrolled mid-year, members with data from multiple source systems, members with exclusion codes applied).

**Chain-of-custody documentation:** Every sampled record is documented with its full lineage path — source system, transformation hops, FHIR resource ID, AuditEvent ID. This documentation becomes the evidence package for the finding.

---

## Step 5 — Finding Classification and Rate Impact Estimation

Each lineage study produces findings classified at three levels:

**Finding level 1 — Lineage gap**
The lineage path is undocumented or partially documented. No machine-readable evidence exists that this transformation produces correct output. Risk: unknown. Action: document gap, recommend lineage tooling implementation.

**Finding level 2 — Transformation error**
The lineage path is documented, but the actual output does not match the documented transformation rules. The discrepancy is confirmed in the sample. Risk: quantified by sample error rate × population size. Action: ETL rule correction, change control documentation, re-validation.

**Finding level 3 — Systematic failure**
The same transformation error appears across multiple members in the sample at a rate suggesting it affects the full population, not just edge cases. Risk: material rate impact, potential audit finding. Action: immediate remediation before measure lock.

**Rate impact estimation:**

For each confirmed finding, estimate the rate impact:

```
Estimated affected members = 
  (sample error rate) × (denominator population)

Rate impact = 
  (affected members with numerator-qualifying events) / 
  (total denominator)
```

A 3% sample error rate in a denominator of 50,000 members, where 40% of affected members have qualifying events, produces an estimated rate impact of approximately 1.2 percentage points. For a measure where the national average is 68%, moving from 66.8% to 68% is the difference between the 50th and 55th percentile — material for a competitive plan.

---

## Velox as a Partner Tool

Velox (or equivalent: OpenLineage/Marquez, dbt lineage, Apache Atlas) is the tool that generates the lineage graph the DQAR assessment queries. The relationship is:

- **Without Velox:** the lineage inventory must be constructed manually from documentation and code review. This is expensive, error-prone, and produces a point-in-time snapshot that degrades immediately. The absence of lineage tooling is itself a Level 6 governance finding.

- **With Velox:** the lineage graph is machine-readable and queryable. Study Type 1 (claims-to-FHIR) and Study Type 2 (EHR feed) can be executed against the graph directly, dramatically reducing manual effort. The DQAR assessment becomes a query against existing lineage metadata rather than a reconstruction exercise.

**Velox in the engagement model:**

Assessment phase: Indicina queries the client's Velox (or OpenLineage) graph to extract the lineage inventory. Where Velox coverage is incomplete, document the gap and supplement with manual inventory.

Roadmap phase: Plans without lineage tooling receive a recommendation to implement Velox or OpenLineage as the highest-priority governance remediation — it's the enabler for everything else.

Implementation phase: Velox implementation is a partner referral. Indicina specifies the lineage coverage requirements (which pipeline hops must be instrumented); the implementation vendor delivers.

**Important clarification:** As of June 2026, Velox is a prospective partner in the Indicina ecosystem, positioned as the plan-side business user platform complementary to Health Samurai's FHIR infrastructure. Velox Health Metadata (veloxhealthmetadata.com) and their 10-10-10 assessment process are the specific product and methodology under evaluation. The lineage tooling role — instrumenting feed-level provenance across the HEDIS pipeline — is a natural fit for the Velox partnership. Before naming Velox in client-facing materials, confirm: (1) specific product capabilities for feed-level lineage documentation, (2) formal partnership agreement status, (3) co-engagement model with Health Samurai. OpenLineage/Marquez remains the safe vendor-neutral reference in client deliverables until the Velox partnership is confirmed.

---

## Differential Sampling at Lineage Checkpoints — The Auditor Service Model

This is the framework that elevates DQAR from a one-time assessment tool into a reusable auditor-grade validation service. The core insight: the same conformance testing logic — `stage1a_bulk_fhir_export_preflight.py`, `stage1b_ndjson_validator.py`, `stage1c_fhir_uscore_validator.py` — can run at multiple points in the data lineage. The **delta between checkpoints is the finding**.

### The Four Validation Checkpoints

```
Checkpoint 1 — Plan's FHIR data store export (outbound)
  What runs:   stage1a preflight + stage1b ndjson + stage1c conformance testing
  Context:     Plan's own FHIR vendor (1UpHealth, AWS HealthLake, etc.)
  Finds:       What is the baseline quality of the plan's own FHIR data?
  Use case:    UC1 client validation kit — plan runs this themselves

Checkpoint 2 — Post PHI redaction (pre-Indicina delivery)
  What runs:   stage1a preflight + stage1b ndjson + stage1c conformance testing
  Context:     Same extract after anonymization, before crossing PHI boundary
  Finds:       Did the PHI redaction process introduce structural errors?
               Delta from Checkpoint 1 = redaction-introduced failures
  Use case:    Path B — confirms anonymized extract integrity before sandbox

Checkpoint 3 — P2P inbound endpoint (UC3 — data arriving from another payer)
  What runs:   stage1a preflight + stage1b ndjson + stage1c conformance testing
               + UC3 three-pass version-aware conformance testing (3.1.1 / 6.1.0 / delta)
  Context:     Bulk FHIR data received via CMS-0057-F P2P API from sending payer
  Finds:       What is the quality of data arriving from external payers?
               Per-sender scorecard — which senders have quality problems,
               which have version gaps, which are clean
  Use case:    UC3 P2P exchange quality assessment

Checkpoint 4 — Indicina Aidbox sandbox (post-ingest re-validation)
  What runs:   stage1b + stage1c re-run on Aidbox write
               + Termbox VSD conformance
               + AuditEvent seven-extension metadata (incl. ol-run-id → OpenLineage graph join)
  Context:     Anonymized extract loaded to sandbox (Path B) or
               PHI extract loaded to plan's own Aidbox (Path C)
  Finds:       Did ingest introduce any new conformance gaps?
               What is the terminology conformance baseline?
  Use case:    Stage 3 of the DQAR pipeline
```

### The Differential Sampling Logic

Running the same validation at multiple checkpoints and comparing results produces a **differential finding** — the gap between two checkpoints identifies exactly where in the lineage a quality problem was introduced.

| Delta | What it means | Finding owner |
|---|---|---|
| CP1 clean → CP2 errors | PHI redaction corrupted structure | Redaction pipeline — Indicina advisory |
| CP1 errors → CP3 same errors | Plan's own data quality problem carried into P2P | Plan remediation |
| CP3 errors not in CP1 | Sending payer introduced the errors | Sending payer — raise data quality SLA |
| CP3 pass 1+2 errors, pass 3 only | US Core version gap artifact | Receiving plan normalization required |
| CP1 clean → CP4 errors | Ingest pipeline or anonymization introduced errors | Pipeline remediation |
| All checkpoints clean | No lineage-introduced quality gaps | Positive finding — governance maturity evidence |

### Sampling Strategy Across Checkpoints

Each checkpoint does not need to validate the full extract. Differential sampling draws a **consistent stratified sample** — the same members, the same resource types — across all checkpoints. This makes the delta calculation precise: the same 500 Condition resources are validated at CP1 and CP3, so any new errors at CP3 are definitively introduced between those two points.

**Sample construction:**
- Select a stratified sample at CP1 (first checkpoint): 30–100 members per study depending on plan size, stratified by source system and resource type
- Apply the same member/resource sample at every subsequent checkpoint
- Track by `resource.id` or `patient.id` — the consistent identifier across checkpoints
- Where PHI redaction replaces patient IDs with tokens, maintain the CP1→CP2 mapping in the token vault

**This is the auditor service Indicina provides that plans cannot perform themselves.** A plan's internal team can run the validation kit at CP1. They cannot independently run CP3 (they are the receiving plan — they need an independent assessor to evaluate what's arriving). They cannot run CP4 without the Indicina/Health Samurai infrastructure. And they cannot compute the differential across checkpoints without a consistent sampling framework and independent record-keeping.

### Engagement Delivery Model

Each checkpoint produces its own JSON report and PDF render using the same report schema. The differential analysis is a fifth report — the **lineage differential report** — that sits above the individual checkpoint reports and shows:

- Checkpoint-by-checkpoint pass/fail matrix per resource type
- Error introduction point — which checkpoint first introduced each error class
- Error persistence — which errors survive all checkpoints (structural problems) vs. which appear at only one checkpoint (introduced errors)
- Governance implication — is this a one-time fix or a systemic pipeline failure?

The lineage differential report maps directly to DQAR Domain 3 findings and feeds the three-tier findings report at Stage 7.

### Reusability Across UC1, UC2, UC3

| Use case | Checkpoints active | Differential value |
|---|---|---|
| UC1 assessment | CP1 + CP2 + CP4 | Baseline quality + redaction integrity + sandbox conformance |
| UC2 monitoring | CP1 on scheduled cadence | Drift detection — CP1 at time T vs. CP1 at time T+90 days |
| UC3 P2P assessment | CP3 + CP4 | Per-sender quality + ingest conformance |
| Full engagement | All four | Complete lineage differential across every hop |

---

## Integration with the DQAR Assessment Deliverable

The five lineage studies are reported in the findings document under Domain 3, with each study producing:

- Study summary (path tested, sample size, method)
- Finding level (gap / transformation error / systematic failure)
- Rate impact estimate
- Governance root cause (Level 6 dimension)
- Remediation recommendation (immediate ETL fix / lineage tooling implementation / change control process)

The differential sampling framework adds a sixth output to each study: the **checkpoint delta** — which lineage hop introduced the error, confirmed by consistent sampling across checkpoints.

The studies collectively answer the question the NCQA IS Assessment cannot: *"Can you trace any member's measure flag back to its originating source record, through every transformation hop, with a machine-readable audit trail?"* If yes, the plan has defensible lineage. If no, the studies document exactly where the chain breaks and what it would take to repair it.
