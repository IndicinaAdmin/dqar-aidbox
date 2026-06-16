# DQAR Use Case Index
**Sonian Consulting Business — Three Active Use Cases**
*Version: June 2026 v2 | Confidential — Internal Reference*

---

## Governing Decisions

**Sonian will not pursue NCQA audit certification.**
Certifying against Vol. 5 — the framework DQAR argues is inadequate — creates a credibility conflict. Staying advisory means Sonian is never competitive with certified auditors, is free to assess dimensions Vol. 5 doesn't cover, and is not tied to the HEDIS calendar.

**All use cases are advisory and consulting services, not certification services.**

**The core value proposition:**
NCQA certifies that the measure logic executes correctly. NCQA DCS explicitly does not validate data mapping or accuracy. DQAR fills that gap — validating the five semantic layers between raw payer data and the CQL engine, and assessing the MDM maturity, metadata management capability, and data governance policies that determine whether data quality is sustainable across measurement periods.

*Someone else certifies the plumbing. Sonian certifies the water.*

**Level 6 governance maturity rubric:** Sonian's proprietary DQAR maturity rubric is structured using the CMMI-DMM five-level progression (Initial → Repeatable → Defined → Managed → Optimized) and grounded in the DAMA-DMBOK knowledge areas for data governance, MDM, metadata management, data quality, and data operations. It is calibrated specifically for payer HEDIS pipeline operations — more actionable than either generic model because it names the specific failure modes, tools, and regulatory deadlines relevant to the buyer. This is Sonian IP with no licensing dependency. DAMA-DMBOK slides and reference material will be uploaded to the DQAR Shared KB project to anchor the rubric development.

---

## Active Use Case Map

| # | Name | Buying trigger | Engagement type | Health Samurai |
|---|---|---|---|---|
| UC1 | Digital Measure Readiness Assessment | MP2029 ECDS cliff; plan doesn't know where they stand | Fixed-fee assessment | Aidbox, Termbox |
| UC2 | Digital Quality Data Operations Monitoring | Plan wants continuous visibility into data quality drift | Recurring subscription | Aidbox, Termbox |
| UC3 | Payer-to-Payer Data Exchange Quality | P2P exchange live or imminent; incoming data quality unknown | Fixed-fee assessment | Aidbox, Termbox |

## Deferred to Phase 2

| # | Name | Rationale for deferral |
|---|---|---|
| — | Pre-Audit Digital Readiness Preparation | Deferred — not abandoned. Sonian's approach lets plans keep current vendor contracts and architectures in place. As DQAR assessments demonstrate more agile, affordable, and compliant workflows for FHIR and dQM, plans will see the case for full migration to Health Samurai — not just for Payerbox and CMS API compliance, but as the ideal digital quality measure reporting environment: reference PostgreSQL with data lineage embedded at ingestion, native measure attribution via AuditEvent, and engine-agnostic CQL execution. Pre-Audit Preparation becomes a natural Phase 2 service once that migration is underway. |
| — | CMS Interoperability Compliance Readiness | Deferred — different buyer (CIO/technology vs. CDO/quality), different regulatory surface. Payerbox partnership with Health Samurai not yet formalized. Phase 2 once the HS partnership matures and UC3 P2P engagements establish the data quality foundation that CMS API compliance depends on. |

---

## Platform Ladder — The Staged Engagement Model

This is the core commercial architecture of the DQAR engagement. The premise: plans need to validate before they commit. Their security and compliance teams need time to complete HIPAA and SOC2 due diligence on Health Samurai before PHI-adjacent infrastructure goes to contract. The ladder gives Sonian productive billable work at every stage while that process runs.

**The governing principle:** Each rung of the ladder delivers real value on its own. A plan that never advances beyond Rung 1 still gets findings they can act on. The ladder is not a sales funnel — it is a use-case-driven expansion path where trust, compliance clearance, and plan maturity grow together.

```
RUNG 1 — Offline Conformance Testing (no PHI leaves the plan, no HS infrastructure required)
  What runs:      Client-side conformance testing kit — Stage 1 (stage1a, stage1b, stage1c)
                  Governance assessment interviews (Track B, Level 6)
                  Feed manifest construction
  What Sonian delivers:  Preliminary findings on structural and conformance gaps
                           Level 6 governance maturity score
                           Prioritized gap inventory
  Cost:           Low fixed-fee or included in retainer
  HS dependency:  None — plan's security team has not yet reviewed HS
  PHI exposure:   Zero — all conformance testing runs on plan infrastructure
  Who can remediate: Plan internal staff, Sonian advisory

RUNG 2 — Anonymized Sandbox Assessment (anonymized data only, HS HIPAA/SOC2 review in parallel)
  What runs:      PHI-redacted ndjson extract loaded to Aidbox sandbox
                  AuditEvent seven-extension ingest
                  Termbox VSD conformance testing
                  SQL on FHIR assessment queries (five measures)
                  Risk stratification matrix from AuditEvent metadata
  What Sonian delivers:  Full three-tier DQAR findings report
                           Measure rate impact estimates
                           Remediation roadmap sequenced against MP2029
  Cost:           UC1 fixed-fee engagement
  HS dependency:  Aidbox + Termbox in Sonian-managed sandbox
                  Plan reviews HS HIPAA BAA and SOC2 report concurrently
                  No plan-side HS contract required at this stage
  PHI exposure:   Zero — anonymized extract only crosses to Sonian/HS sandbox
  Who can remediate: Plan internal, Sonian, or HS staff per plan's choice

RUNG 3 — Continuous Monitoring with Plan-Controlled Infrastructure (HS contract in place)
  What runs:      UC2 monthly/quarterly monitoring cadence
                  Termbox client-hosted or Sonian-sandbox per SOW
                  VSD refresh validation at measurement period rollover
                  Level 5 population anomaly detection
  What Sonian delivers:  Quarterly digital quality scorecard
                           Governance maturity progression tracking
                           Drift alerts between scheduled reviews
  Cost:           $4K/month retainer
  HS dependency:  Aidbox and/or Termbox licensing — plan has completed
                  HIPAA BAA and SOC2 review, contract in place
  PHI exposure:   Managed under HS BAA — plan controls their own instance
  Who can remediate: Plan internal, Sonian, or HS staff per plan's choice

RUNG 4 — Full PHI Operational Mode (Path C — target state)
  What changes:   No PHI redaction step. Bulk FHIR extract loads
                  directly to plan's own Aidbox instance with full PHI.
                  The conformance testing kit becomes the pre-ingest quality
                  gate for real production operations, not assessment.
                  AuditEvent metadata is permanent production lineage
                  from day one — not a sandbox artifact.
  What Sonian delivers:  Ongoing UC2 monitoring against plan's
                           live Aidbox instance. Quarterly scorecard,
                           drift detection, maturity progression.
                           Assessment queries run on scheduled cadence.
  Cost:           $4K/month retainer + HS Aidbox/Termbox licensing
  HS dependency:  Plan has completed HIPAA BAA + SOC2 review.
                  Aidbox contracted and in production.
  PHI exposure:   Plan-owned Aidbox under plan's own BAA.
                  Sonian accesses via governed query interface only.
  Who can remediate: Plan internal, Sonian, or HS staff per plan's choice
  
  This is the destination the entire ladder is designed to reach.
  The plan's FHIR infrastructure is now plan-controlled, lineage
  is native and continuous, measure runs have no per-run vendor
  cost, and Sonian provides independent ongoing validation
  rather than a one-time assessment.
```

**The due diligence window is productive time, not dead time.** While the plan's security team reviews HS HIPAA attestations and SOC2 Type II report, Sonian is running Rung 1 and Rung 2 work. By the time compliance clearance arrives, the plan already has a full findings report, a remediation roadmap, and a governance maturity baseline. The HS contract unlocks the next layer — it is not the starting gate.

**The Velox boundary on this ladder:** Velox operates on the plan-side business user layer and does not require PHI access. Velox can be introduced at Rung 2 or Rung 3 without waiting for Rung 4 full infrastructure — the Velox dashboard consumes findings outputs and quality scorecard data, not raw FHIR. The Rung 1 offline validation kit is embeddable in Velox's onboarding workflow as a complementary capability.

---

## UC1 — Digital Measure Readiness Assessment

**What it is:** A structured assessment of a plan's readiness for ECDS mandatory reporting. Anonymized Bulk FHIR extract loaded into an Aidbox sandbox. Both assessment tracks run in parallel: five-level semantic validation (Track A) and Level 6 governance capability assessment (Track B using DQAR maturity rubric).

**Pitch:** *"NCQA DCS certifies your engine runs correctly. We assess whether the data going into it is semantically trustworthy — the right codes, in the right resources, in the right clinical context, with plausible values, governed by processes that will keep them right next year."*

**Buying trigger:** Plan leadership aware of MP2029 ECDS mandatory reporting deadline without a clear picture of current digital measure infrastructure gaps. Often triggered by new VP of Quality, CIO initiative, or vendor pitch surfacing the issue.

**Buyer:** VP of Quality, Chief Data Officer, VP of Analytics.

**Deliverable:** Three-tier DQAR findings report organized by semantic level and governance sub-domain. Each finding carries technical severity AND governance root cause AND DAMA-DMBOK-anchored maturity score. Prioritized remediation roadmap sequenced against MP2026 and MP2029 milestones.

**Platform ladder entry point:** UC1 spans Rungs 1 and 2. Rung 1 (offline validation kit + governance interviews) can begin immediately with no vendor contracts. Rung 2 (Aidbox sandbox assessment) runs while plan security reviews HS documentation. Full findings report delivered at Rung 2 completion.

**Engagement structure:**
- Client provides feed manifest (engagement kickoff) declaring all source system feeds
- Client provides anonymized Bulk FHIR export (ndjson via `$export`) + VSD access (Mode 1, 2, or 3)
- Client runs Sonian-provided conformance testing kit on own infrastructure — PHI never leaves client environment:
  - Stage 1: Bulk FHIR API conformance (live server test)
  - Stage 2: ndjson structural conformance testing
  - Stage 3a: Base FHIR R4 (v4.0.1) structural conformance testing
  - Stage 3: US Core 6.1.0 profile conformance
- Anonymized extract + three conformance reports delivered to Sonian
- Sonian loads to Aidbox sandbox with AuditEvent + seven extension metadata fields generated atomically
- Level 6 governance assessment via structured interviews and documentation review
- Findings report and roadmap delivered

**Level 6 assessment scope (DAMA-DMBOK knowledge areas):**
- Data Governance — change control authority, ownership, enforcement
- Master Data Management — member, provider, terminology MDM
- Metadata Management — data catalog coverage, field-level lineage, VSD governance
- Data Quality — proactive standards vs. reactive remediation
- Data Operations — ETL governance, vendor SLAs, pipeline change management

**PIQI integration — Domain 5 (Population Completeness):**
PIQI framework dimensions map directly to Domain 5 procedures: Usability → 834 enrollment reconciliation; Plausibility → continuous enrollment logic audit; Comparability → clinical data completeness by provider; Stability → population-level anomaly detection (Level 5, scikit-learn/PyOD).

**Technical implementation:** UC1 Assessment App — `dqar-06-uc1-app-technical-specification.md`
**Built with:** Claude Code + Health Samurai (Aidbox + Termbox)
**Framework linkage:** Implements DQAR Domains 2, 3, 6. Full framework in DQAR Shared KB.
**Inference algorithm:** `dqar-05-source-inference-algorithm.md` — Priority 1–4 deterministic, Priority 5 probabilistic classifier (heuristic — findings based on Priority 5 must be qualified accordingly), Priority 6 circumstantial.

**Revenue model:** Fixed-fee. Standalone — does not require plan to adopt any vendor platform.

**Downstream opportunity:** Level 6 governance findings create qualified leads for UC2 (monitoring). Value set drift findings create Termbox referrals. Feed manifest gaps create data governance advisory leads.

---

## UC2 — Digital Quality Data Operations Monitoring

**What it is:** A recurring subscription service providing continuous DQAR conformance monitoring against the plan's FHIR pipeline. Runs Track A Levels 1–3 on a scheduled cadence, reassesses Level 6 governance maturity every six months, produces quarterly findings scorecard with drift detection and trending. Sonian sells the conformance testing methodology and monitoring cadence — the plan owns the terminology data and pipeline infrastructure.

**Pitch:** *"Data quality is continuous. The audit is annual. By the time audit season reveals a value set drift or semantic failure, the problem has been affecting your rates for months. Continuous monitoring catches it in real time — and tracks your governance maturity improvement toward MP2029 readiness."*

**Buying trigger:** One of three triggers:
1. UC1 findings identified Level 6 governance gaps — plan wants ongoing monitoring during remediation
2. Plan has had measure rate anomalies they couldn't explain — reactive quality improvement
3. Plan is preparing for ECDS mandatory reporting and wants continuous conformance visibility

**Buyer:** VP of Quality, VP of Analytics, or Chief Data Officer. Typically a follow-on from a UC1 engagement.

**Deliverable:** Quarterly digital quality scorecard:
- RAG status per semantic level (1–5) and governance sub-domain
- Drift detection — conformance changes since prior quarter
- Maturity progression — DAMA-DMBOK-anchored score movement toward Level 3 (MP2029 floor)
- Anomaly alerts between scheduled reviews (Level 5 population coherence failures)
- Annual VSD refresh validation at measurement period rollover

**VSD model:** Client holds the NCQA license. Sonian holds the conformance test suite and monitoring methodology. Client runs Termbox instance or provides annual VSD export per SOW.

**Monitoring cadence:**
- Track A Levels 1–3: monthly automated conformance run
- Track A Levels 4–5: quarterly (population-level anomaly detection requires sufficient volume)
- Level 6 governance reassessment: semi-annual structured review
- VSD currency check: at NCQA measurement period release + 30 days

**CMMI-DMM progression narrative:** The UC1 engagement establishes the baseline maturity scores per DAMA-DMBOK knowledge area. UC2 tracks movement up the five-level scale each quarter. Most plans assessed at 1–2 across MDM and metadata. Level 3 is the MP2029 readiness floor — UC2 provides the roadmap and evidence of progress.

**Revenue model:** Annual subscription. Most defensible recurring revenue — VSD changes every year, monitoring need is continuous, maturity improvement is multi-year. Requires prior UC1 engagement as baseline.

**Health Samurai role:** Termbox as client-hosted or Sonian-sandbox terminology server. Aidbox for any in-engagement data loading.

---

## UC3 — Payer-to-Payer Data Exchange Quality

**What it is:** Assessment of the quality of clinical and claims data *received* via Payer-to-Payer API exchange before it enters the receiving plan's FHIR pipeline and affects HEDIS denominators, HCC risk scores, or member economics. The defining characteristic: the receiving plan did not generate this data and cannot control its quality — but they are liable for decisions made from it.

**Pitch:** *"CMS gives you the pipe. UC3 tells you what's actually flowing through it. UCare received an enrollment cascade they couldn't risk-assess because their analytics infrastructure couldn't leverage the clinical data that was theoretically available. A plan with FHIR-native architecture, governed P2P data quality assessment, and SQL on FHIR analytics turns that data into a competitive advantage. Without it, five years of clinical history on transitioning members sits siloed and unused while the losses accumulate."*

**Case study:** UCare (Minnesota) 2025 collapse. ~20% enrollment increase from displaced UnitedHealthcare/Humana members during AEP 2024. Inadequate risk data on transitioning population. Total losses: $504M. The data was theoretically available via P2P exchange. The capability to assess and use it was not. Source: John Hoff, MTR Group, LinkedIn June 2026.

**Regulatory anchor:** CMS-0057-F Payer-to-Payer API mandatory by January 1, 2027.

**Buying trigger:** Plan implementing P2P data exchange and analytics team concerned about incoming data quality. Or plan notices HEDIS denominator or HCC anomalies after P2P exchange goes live.

**Buyer:** VP of Analytics, Chief Data Officer, VP of Quality. Most technically sophisticated buyer in the portfolio.

---

### P2P Format Stack — Critical for UC3 Scope

P2P data received under CMS-0057-F arrives in a three-layer format stack:

**Layer 1 — Transport: Bulk FHIR (mandatory)**
Bulk Payer-to-Payer exchange SHALL use FHIR Bulk Data Access IG STU2 (2.0.0) asynchronous semantics. Same ndjson transport as UC1. Stage 1 Bulk FHIR API conformance testing applies.

**Layer 2 — Content: US Core 3.1.1 OR 6.1.0 (both possible)**
CMS-0057-F requires support for USCDI v1 (US Core 3.1.1) and USCDI v3 (US Core 6.1.0). A sending payer on the original CMS-9115 (2021) implementation may be sending 3.1.1-vintage resources. A sending payer on a forward-compliant implementation sends 6.1.0. The receiving plan has no control over which version arrives.

**Layer 3 — Profile: Da Vinci PDex (recommended, not required)**
CMS recommends PDex IG for provenance support. PDex-conformant senders include Provenance resources with transmitted data — this inverts the UC1 inference challenge. A UC3 assessment that finds PDex Provenance in incoming data should flag this as a positive — the sending payer is ahead of most internal pipelines on provenance implementation.

**What's included:** Up to 5 years of claims, encounters, USCDI data elements, and prior auth history. Member consent (Consent resource) required for opt-in.

---

### The Version Gap — The Built-In Quality Risk

This is the commercially defining insight for UC3. The version gap between US Core 3.1.1 and 6.1.0 is not a technical edge case — it is a structural problem baked into the current regulatory framework affecting every receiving plan today.

**Why it exists:** CMS-9115-F (2020) required Patient Access API on US Core 3.1.1 / USCDI v1. CMS-0057-F (2024) upgraded to US Core 6.1.0 for new APIs including P2P. CMS did not require existing 3.1.1 implementations to upgrade before the P2P deadline. A plan that built FHIR infrastructure in 2021 on 3.1.1 is still compliant with their original mandate — and will send 3.1.1 data through P2P starting Jan 1 2027.

**HEDIS-relevant delta between 3.1.1 and 6.1.0:**

| Element | 3.1.1 status | 6.1.0 status | HEDIS impact |
|---|---|---|---|
| `Encounter.type` | Present, not MUST SUPPORT | MUST SUPPORT | CBP, CDC, FUH/FUM encounter type constraints fail without it |
| `Observation.category` | Present, not consistently required | MUST SUPPORT per profile | Source-type inference drops to medium/low confidence |
| `DiagnosticReport` | Single profile | Split lab/clinical note profiles | Wrong profile selected, false validation errors |
| `Observation` (blood pressure) | Less constrained | Tightly constrained component structure + UCUM units | CBP numerator validation failures |
| `MedicationRequest.dosageInstruction` | Optional | MUST SUPPORT | Medication adherence measure gaps |
| `Patient.race/ethnicity` | US Core extensions | USCDI v3 restructured elements | Demographic constraint application failures |

**Three-pass conformance testing for UC3:**

This is the methodology that makes UC3 findings actionable rather than a list of undifferentiated errors:

```
Pass 1 — Base FHIR R4 structural conformance testing
  Errors = genuine structural failures
  Finding: Sending payer implementation quality problem
  Owner: Request retransmission / raise data quality SLA

Pass 2 — US Core 3.1.1 conformance
  New errors vs Pass 1 = 3.1.1 non-conformance
  Finding: Sending payer quality failure against their own standard
  Owner: Request retransmission / raise data quality SLA

Pass 3 — US Core 6.1.0 conformance
  New errors vs Pass 2 = version gap artifacts
  Finding: Regulatory transition mismatch — NOT sending payer's fault
  Owner: Receiving plan must implement version normalization on ingest
```

**Error classification table:**

| Error pattern | Classification | Action |
|---|---|---|
| Pass 1 only | Structural failure | Request retransmission from sending payer |
| Pass 1 + 2 | 3.1.1 non-conformance | Raise data quality SLA with sending payer |
| Pass 3 only | Version gap artifact | Implement receiving-plan normalization |
| Pass 2 + 3 | Genuine data quality problem | Investigate regardless of version |

**Version detection before conformance testing:**

Before running passes, detect which US Core version each incoming feed is using:
1. `meta.profile` declarations on resources — most reliable if populated
2. `GET [sending-payer-base]/metadata` CapabilityStatement — query before bulk export, add version to feed manifest
3. Structural fingerprinting — presence/absence of 6.1.0-specific MUST SUPPORT elements in a resource sample

Grouping incoming resources by `source-feed-id` (AuditEvent extension) and detecting US Core version per feed turns a chaotic multi-sender conformance testing problem into a structured per-sender quality assessment.

---

### UC3 Deliverable

**Incoming P2P data quality assessment** covering all five semantic levels applied to *received* data:

- Stage 1: Bulk FHIR API conformance (live server test)
- Stage 2: ndjson structural conformance testing
- Stage 3: Three-pass version-aware conformance (3.1.1 → 6.1.0 → delta classification)
- Level 3: Measure context constraint validation against receiving plan's HEDIS measures
- Level 4: Clinical plausibility of received data
- Level 5: Population completeness — all expected members and historical records arriving?
- Level 6 (receiving plan): Governance assessment of P2P ingest process — is received data governed before entering the pipeline?
- Consent resource validity check — FHIR Consent resources documenting member opt-in
- Provenance coverage — PDex Provenance resources present? If so, flag as positive; if absent, document gap

**Recommendation per feed:** accept as-is | transform on ingest | reject and request retransmission

**Per-sender quality scorecard:** Each sending payer's data assessed separately. Version vintage identified. Error classification table applied. Receiving plan knows exactly which senders have quality problems, which have version gaps, and which are clean.

**Key framing from industry dialogue (Michael E. Campbell, LinkedIn, June 2026):** *"Any strategic advantage on payer to payer exchange depends on several data concerns. How complete is the payer data — most clinical data is left out of FHIR by default and most plans don't use FHIR data for analytics. It's still treated as a data source incompatible with legacy analytic platforms. A plan with FHIR native architecture, broad scope of included data, and SQL on FHIR or similar analytic environments can leverage that data while others leave it siloed."*

**Competitive position:** Most forward-looking and least crowded space in the portfolio. Almost no one is providing P2P data quality assessment services. First-mover advantage is meaningful — the Jan 1 2027 deadline creates urgency now.

**Revenue model:** Fixed-fee assessment. Evolves into UC2-style continuous monitoring on the P2P ingest pipeline as P2P exchange volume grows.

**Health Samurai role:** Aidbox as receiving FHIR server sandbox with Termbox validation on ingest. AuditEvent seven-extension pattern applied — tag each received resource with P2P sending-plan feed ID at ingest.

**Technical infrastructure:** Shares UC1 pipeline architecture with three additions:
1. Dual-version US Core conformance testing (3.1.1 and 6.1.0) with delta classification
2. Da Vinci PDex profile conformance testing as optional third pass
3. FHIR Consent resource validity check

---

## Engagement Architecture — Three Use Cases

### The Three-Phase Model

**Phase 1 — Assessment (Sonian-led)**
Fixed-fee. Vendor-neutral. DQAR framework applied. Three-tier findings report with semantic level breakdown, version-aware conformance classification (UC3), and DAMA-DMBOK-anchored governance maturity scores. No partner products required at this phase. Sonian provides the validation services the plan does not have internal bandwidth to perform.

**Phase 2 — Roadmap (Sonian-led)**
Prioritized implementation roadmap sequenced against MP2026/MP2029 (UC1) or Jan 1 2027 (UC3). Partner products named — Aidbox, Termbox, Velox — with specific gap-to-solution mapping. Remediation path left to the plan's discretion.

**Phase 3 — Remediation (plan's choice of path)**
Three options — the plan chooses based on internal capacity and urgency:

| Path | Who does the work | Sonian role |
|---|---|---|
| Internal staff | Plan's own engineering and informatics teams | Findings report + roadmap; available for advisory questions |
| Sonian staff | Sonian provides hands-on remediation advisory and implementation oversight | Active engagement; validates that each fix closes the finding |
| Health Samurai staff | Health Samurai implements FHIR infrastructure gaps (Aidbox, Termbox, Interbox) | Independent validation that remediation closes the finding; ongoing advisory |

All three paths are compatible with the $4K/month retainer — the retainer funds Sonian's ongoing validation role regardless of who does the implementation work.

### Revenue Progression

| Phase | Sonian revenue | Health Samurai revenue | Velox revenue |
|---|---|---|---|
| UC1 Assessment | Fixed-fee | None | None |
| UC1 Roadmap | Fixed-fee | None | None |
| UC1 Implementation advisory | $4K/month retainer | Aidbox + Termbox licensing | Lineage tooling referral |
| UC2 Monitoring subscription | $4K/month retainer | Termbox subscription | Lineage monitoring |
| UC3 Assessment | Fixed-fee | None | None |
| UC3 → UC2 Monitoring | $4K/month retainer | Aidbox + Termbox subscription | Feed lineage tooling |

**Ongoing retainer model ($4,000/month):** Assessment is not a one-time event. After the initial findings report, the retainer covers continuous monitoring, VSD refresh advisory, governance maturity progression tracking, implementation oversight, and access to Sonian's expert network and partner best practices. The retainer is the mechanism by which the Health Samurai and Velox relationships deepen over time — each quarter introduces additional platform capabilities as the plan's remediation matures.

### Assessment Objectivity — The Commercial Logic

Sonian is an audit readiness assessor and consultant — not a certified NCQA auditor. This distinction matters commercially: Sonian is not constrained by auditor independence rules, and can assess, advise on remediation, oversee implementation, and monitor continuously with the same client across multiple years. This is the foundation of the $4K/month ongoing engagement model.

Assessment objectivity is preserved through structure, not role prohibition:

1. **Assessment phase is vendor-neutral and fixed-fee.** Findings stand on their own before any partner product is named. The three-tier DQAR report is the deliverable — not a sales pitch for an implementation platform.
2. **Partner products are named in the roadmap phase** after findings are documented, with specific gap-to-solution mapping. Health Samurai products are recommended where they are the right fit — not as a default.
3. **Transparency with clients.** Health Samurai is a preferred FHIR infrastructure partner. Velox is a prospective partner for plan-side business user tooling and lineage. Clients know this. The assessment findings are independently defensible regardless of which implementation path the plan chooses.

The goal is a growing partner ecosystem — Health Samurai for FHIR infrastructure and data engineering, Velox for plan-side business user platforms — where Sonian's assessment credibility creates qualified implementation referrals, and partner relationships deepen the engagement surface for clients.

---

## Shared Infrastructure — Three Active Use Cases

| Component | UC1 | UC2 | UC3 |
|---|---|---|---|
| DQAR six audit domains | All | Domains 2,3,6 | Domains 2,3,4,5 |
| Five-level semantic validation | Track A | Levels 1-3 scheduled | All five (incoming data) |
| Level 6 DAMA-DMBOK rubric | Full | Semi-annual reassessment | Receiving-plan governance |
| Feed manifest | Required | Ongoing maintenance | Required per sending payer |
| Aidbox sandbox | Assessment | Monitoring | Assessment |
| Termbox VSD | Mode 1/2/3 | Client-hosted / SOW | Mode 1/2/3 |
| AuditEvent seven extensions | Full | Scheduled | Full + sending-payer-id |
| Source inference algorithm | Full | Scheduled | Full + version detection |
| SQL on FHIR query library | Five measures | Scheduled | Five measures (incoming) |
| Client conformance testing kit | UC1 standard | Reused | UC3 three-pass version |
| PIQI framework (Domain 5) | Full | Level 5 monthly | Full (incoming data) |
| US Core version detection | 6.1.0 only | 6.1.0 drift | 3.1.1 + 6.1.0 + delta |
| PDex profile conformance testing | Not applicable | Not applicable | Optional third pass |
| Consent resource check | Not applicable | Not applicable | Required |

---

## Project Architecture

### Four-project structure

**Project 1 — DQAR Shared KB** (authoritative framework)
Framework critique, six domains, three-tier findings, five-level semantic validation, Level 6 DAMA-DMBOK maturity rubric, regulatory timeline, Health Samurai partner guide, inference algorithm, lineage studies methodology, PIQI Domain 5 integration, CMMI-DMM level structure. DAMA slides to be uploaded. No application code.

**Project 2 — DQAR UC1 Assessment App** (Claude Code + Health Samurai)
Eight-stage conformance testing and assessment pipeline, Aidbox sandbox, SQL on FHIR library, AuditEvent seven extensions, source inference, client conformance testing kit, findings report generator. Primary spec: `dqar-06-uc1-app-technical-specification.md`.

**Project 3 — DQAR UC2 Monitoring Service** (advisory + subscription product)
Monitoring cadence design, drift detection methodology, quarterly scorecard format, DAMA-DMBOK maturity progression tracking, VSD refresh service design, subscription commercial model. Reuses UC1 app infrastructure on scheduled cadence.

**Project 4 — DQAR UC3 P2P Exchange Quality** (advisory)
P2P format stack (Bulk FHIR + US Core 3.1.1/6.1.0 + PDex), three-pass version-aware conformance testing methodology, error classification table, version detection methodology, per-sender scorecard design, Consent validity check, UCare case study. Extends UC1 infrastructure with dual-version and PDex conformance testing.

### Cross-project linkage

Every project uploads from DQAR Shared KB:
- `dqar-01-framework-summary.md`
- `dqar-02-health-samurai-partner-guide.md`
- `dqar-03-use-case-index.md` (this file)
- `dqar-04-lineage-studies-methodology.md`
- `dqar-05-source-inference-algorithm.md`

UC1 app and UC3 additionally upload:
- `dqar-06-uc1-app-technical-specification.md`
- `DQAR_Bulk_FHIR_Extract_Specification_v1.0.docx`
