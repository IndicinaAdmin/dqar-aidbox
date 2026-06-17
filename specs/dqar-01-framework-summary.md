# DQAR Framework Summary
**Digital Quality Audit Readiness — Sonian**
*Version: June 2026 (updated: NCQA ECDS page Jan 2026 + hybrid retirement calendar; CDG-MM maturity model integrated Jun 2026; AuditEvent seven-extension provenance architecture Jun 2026) | Confidential — Internal Reference*

---

## What DQAR Is

The Digital Quality Audit Readiness (DQAR) is Sonian's proprietary methodology for assessing health payer readiness for digital quality reporting. It replaces the manual, PSV-heavy HEDIS compliance audit paradigm with a FHIR-native, automated, standards-conformant, and semantically rigorous assessment framework.

**Sonian's position:** Sonian provides the validation services that health plans do not have the internal bandwidth to perform. Most plans have quality and analytics staff who understand HEDIS reporting — they do not have staff with the FHIR semantic validation, data lineage, and digital measure readiness expertise to assess their own pipelines rigorously. Sonian fills that gap.

Sonian does not pursue NCQA audit certification and does not act as a certified HEDIS auditor. The DQAR is a pre-audit readiness and digital transformation assessment service — the independent validation layer that sits upstream of the certified audit and upstream of the plan's own quality team.

**Remediation is the plan's choice.** The DQAR assessment produces findings. What the plan does with those findings is entirely up to them:
- **Internal staff** — the plan remediates using their own engineering and informatics teams. Sonian's findings report gives them the prioritized roadmap.
- **Sonian staff** — Sonian provides hands-on remediation advisory, implementation oversight, and validation of the fix. The $4K/month retainer covers this ongoing engagement.
- **Health Samurai staff** — where findings point to FHIR infrastructure gaps (Aidbox configuration, Termbox integration, Interbox pipeline instrumentation), Health Samurai provides the implementation. Sonian remains as independent validation that the remediation actually closes the finding.

This flexibility is a feature, not a gap. Plans at different maturity levels need different remediation paths. A plan with strong internal engineering needs only the findings and roadmap. A plan with no internal FHIR capability needs Sonian and Health Samurai to do the work. The assessment is the constant; the remediation path is the plan's decision.

---

## The Data Governance Consulting Product Suite — High-Level Principles

DQAR is the technical core of a four-part consulting suite that takes a health plan from "we don't know where we stand" to "we own a governed, FHIR-native digital-quality pipeline." The four offerings form a single funnel — **survey → train → assess → remediate** — in which each product de-risks and creates pull for the next.

1. **Computable Data Governance Readiness Survey** — a low-cost, top-of-funnel maturity diagnostic. Scores a plan against the **CDG-MM (Computable Data Governance Maturity Model)** — Sonian's clean-room 1–5 maturity ladder across five capability pillars, with a derived Governance Index — in vocabulary the CDO already recognizes. One survey question maps to each of the 15 CDG-MM cells, producing an indicative maturity band. It estimates the gap and routes the plan forward; it does not replace the assessment, which proves the gap with evidence.
2. **Computable Data Governance Training Program** — builds the internal sponsorship, vocabulary, and capability a plan needs to govern a FHIR-native pipeline and act on DQAR findings. Spine is the DGI 7-step governance life cycle; body is the DAMA-DMBOK knowledge areas plus digital-quality literacy (ECDS vs. dQM, the MY2029 calendar, the five-level semantic validation model, and the CDG-MM maturity ladder + Governance Index). Consistent with the CDG-MM design rule, the bodies of knowledge (DAMA-DMBOK, DGI) supply *vocabulary the CDO already recognizes*; the maturity scoring itself is the proprietary CDG-MM.
3. **Health-Payer Data Governance Assessment for Digital Quality** — the paid core, i.e., the DQAR engagement itself: two parallel tracks (five-level semantic validation + CDG-MM governance maturity scoring), six domains, three-tier findings. This is the independent validation layer described above.
4. **Advisement & Remediation (incl. Health Samurai)** — the recurring-revenue engine that acts on findings via the three remediation paths, the Aidbox / Termbox / Interbox stack, the upstream AuditEvent provenance migration advisory, and the $4K/month retainer.

**Governing principles across all four products:**

- **Independence is the brand.** Sonian assesses and validates; it never becomes the sole implementer of what it validates. Where Health Samurai builds, Sonian remains the independent layer confirming the finding is actually closed. This is the structural answer to the conflict-of-interest problem that plagues both the certified-auditor relationship and the incumbent-vendor "we validate ourselves" model.
- **The frameworks are the credibility layer; DQAR is the product.** Lead with the buyer's own canon — DAMA-DMBOK knowledge areas, the DGI operating model, the AWS "governance is the plan, management is the action" distinction — and close on the operationalization. The bodies of knowledge supply the *vocabulary* the CDO recognizes; the maturity ladder, level descriptors, and scoring rigor are Sonian's own clean-room **CDG-MM**, carrying no licensing dependency on any subscription-gated maturity model. DQAR then operationalizes both for the specific failure modes, tools, and regulatory deadlines of payer HEDIS / digital-quality operations.
- **Governance belongs upstream, not at the warehouse tail.** Every product reinforces the L.A. Care lesson — quality and lineage must be governed at ingestion, the earliest and cheapest point to catch error — which is exactly what the upstream AuditEvent migration advisory delivers.
- **Maturity is a ladder, measured against a baseline.** Level 3 (Governed) on the CDG-MM is the MY2029 readiness floor. The CDG-MM is the **scoring spine of the funnel**: the Survey establishes an indicative baseline band, the Assessment scores all 15 cells rigorously with evidence, and the UC2 monitoring subscription re-scores each quarter to show the climb — you cannot demonstrate improvement without a starting score.
- **Every artifact routes forward.** Survey findings route to Training (capability gap) or Assessment (technical/data gap); Assessment findings justify Remediation; Remediation seeds the monitoring subscription. No dead ends, no orphaned deliverables.

---

## The Core Thesis

Most U.S. health payers have:
- A FHIR surface that passes structural conformance testing ✅
- A data lakehouse for claims analytics ✅
- **Nothing between those layers that validates whether clinical data feeding HEDIS measure execution actually means what the measure specification requires** ❌

This semantic validation gap is the primary locus of HEDIS audit failure and digital measure readiness risk.

### The Calibration Problem — Primary Marketing Pitch

> *"A one-week IS assessment with staff interviews and system demonstrations cannot assess this complexity. The audit was calibrated for a 500,000-member commercial plan with a claims system and a spreadsheet-based supplemental data process. It is not calibrated for a 5-million-member multi-product payer with a cloud data lakehouse, five upstream data vendors, and a FHIR API surface serving Prior Auth and payer-to-payer data exchange simultaneously."*

Condensed version:
> *"The audit was calibrated for a 500K-member plan with a claims system and spreadsheet supplemental data. It is not calibrated for a 5M-member payer with a cloud data lakehouse, five upstream vendors, and a FHIR API surface serving Prior Auth and payer-to-payer data exchange simultaneously."*

### The NCQA DCS Positioning — Secondary Marketing Pitch

> *"NCQA certifies that the measure logic is correct. NCQA's Digital Content Services explicitly does not validate your data mapping or accuracy. DQAR fills that gap — validating the five semantic layers between your raw payer data and your CQL engine, and scoring your data governance maturity on the CDG-MM (inventory, metadata, MDM, data quality, and lineage, with a derived Governance Index) that determines whether your data quality is sustainable across measurement periods. Without both, you have a precisely executed calculation on ungoverned inputs."*

**Source:** NCQA Digital Content Services Customer Handbook (April 2025): *"Successful Implementation confirms that Licensee successfully installed the Digital Content Services Application or Licensee Engine, and the Measures. It does not confirm the Licensee's data mapping, data accuracy or implementation of the NCQA FHIR IG."*

This is not a weakness in NCQA DCS — it is a deliberate scope boundary. NCQA is a measure standards body, not a data operations company. DQAR fills the upstream gap DCS explicitly does not cover.

---

## The Three-Tier Findings Structure

Every DQAR engagement produces findings organized into three tiers. This structure reflects Sonian's assessment scope — broader, more technical, and more forward-looking than a HEDIS compliance audit. A certified HEDIS auditor produces a compliance checklist against NCQA Vol. 5. DQAR produces a governance maturity assessment, a data quality analysis, and a digital readiness roadmap — three distinct outputs that together answer questions the NCQA audit was never designed to address.

| Tier | Name | Definition | Example |
|---|---|---|---|
| 1 | Governance gap | A failure in data governance capability — change control, MDM, metadata management, or data operations — that has produced or will produce measure rate impact. Root cause is organizational. | No change control process for value set bindings — retired codes active for two measurement periods undetected; ETL rule modified post-lock with no documented approval |
| 2 | Measure data gap | A data quality failure directly affecting measure rates now — wrong codes, wrong resources, wrong clinical context, broken lineage hop. Root cause is technical and correctable. | LOINC mapped incorrectly for HbA1c — CDC numerator members silently excluded; Encounter.type constraint missing — CBP denominator inflated |
| 3 | Digital readiness gap | A capability gap relative to MY2029 ECDS mandatory reporting or CMS-0057-F P2P requirements. Not failing today — will fail the MY2029 transition without remediation. | No AuditEvent logging on FHIR server; lineage graph terminates at lakehouse boundary; no provenance metadata on clinical resources |

**Tier 1 is the governance dimension.** A plan can fix a Tier 2 finding — patch the ETL rule, update the value set — and leave the Tier 1 governance failure untouched, producing the same class of error next measurement period. The three-tier structure forces both the technical problem and its governance root cause into every finding. That is what a CDO needs to remediate structurally, not just seasonally.

**Tier 3 is the competitive moat.** Invisible to the NCQA audit because that framework does not assess MY2029 readiness. A plan can pass their NCQA audit with a clean bill of health and carry a full slate of Tier 3 findings that will cause them to fail the MY2029 ECDS transition.

Every finding carries two dimensions regardless of tier:
- **Technical severity** — what is broken now and what is the measure rate impact
- **Governance root cause** — why it broke and whether the organization has the capability to prevent recurrence

---

## The Assessment Framework — Two Parallel Tracks

### Track A — Five-Level Semantic Validation (Technical)

Assesses what the data *is* right now. Point-in-time. Executable against a Bulk FHIR extract in the Aidbox assessment sandbox.

**Level 1 — Terminology conformance**
Is the code in the correct NCQA-published value set for the correct measurement period?
- Tool: Termbox + VSD conformance testing
- Answers: "is this code valid for this measure?"
- Does NOT answer: "is this code being used correctly in this clinical context?"

**Level 2 — Resource structural conformance**
Does the FHIR resource conform to US Core and QI Core profiles? Is the code in the right field?
- Tool: HAPI FHIR Validator
- Answers: "does this resource conform to the IG?"
- Does NOT answer: "does this resource represent the right clinical event for this measure?"

**Level 3 — Context conformance** (measure logic awareness required)
Is the resource type correct? Is the encounter type constraint enforced? Does the resource date fall within the measurement period?
- Tool: SQL on FHIR v2 ViewDefinition queries against Aidbox/Postgres
- Answers: "is this resource being used in the right clinical context for this measure?"
- Requires: knowledge of the HEDIS measure specification, not just the value set

**Level 4 — Clinical plausibility**
Does the data make physiological and logical sense?
- Tool: PIQI-style plausibility rules as SQL checks
- Checks: HbA1c values outside physiological range, encounter dates predating enrollment, diagnosis codes inconsistent with age or sex, lab results without performing organization
- Answers: "is this data clinically believable?"

**Level 5 — Population-level semantic coherence**
Is the distribution of codes across the population plausible? Are there systematic anomalies suggesting pipeline failures rather than clinical patterns?
- Tool: scikit-learn/PyOD anomaly detection (Isolation Forest, DBSCAN, One-Class SVM)
- Checks: sudden code frequency spikes, zero clinical records from high-volume PCPs, implausible population-level distributions
- Note: requires sufficient population volume — most meaningful in continuous monitoring (UC3) rather than sample-based assessment (UC1/UC2)

**Important:** Terminology conformance (Level 1) alone does not constitute semantic validation. All five levels are required. A plan can have 100% VSD conformance and produce completely wrong measure rates if Levels 2–5 are broken.

---

### Track B — Level 6 Governance and Management Capability: the CDG-MM (Organizational)

Assesses whether the organization can *sustain* data quality over time. Assessed through structured interviews, documentation review, and artifact inspection — and, at the upper levels, evidenced by computation rather than judgment. This is the organizational layer that sits above the five semantic-validation levels of Track A; it is scored using the **Computable Data Governance Maturity Model (CDG-MM)**, Sonian's proprietary, clean-room maturity framework.

**Why "computable" is the through-line.** FHIR makes health data machine-readable, digital quality measures are computable measure content, and AI is only as trustworthy as the data feeding it — all three demand the same governed, computable foundation. The CDG-MM governs data *to be computed on*, and uses computable instruments (conformance engines, PIQI-style rule scoring) to measure how well a plan can do it. It carries no dependency on any licensed, subscription-gated maturity model.

#### The CDG-MM Maturity Ladder (1–5)

Original plain-language labels; applied identically to every pillar × dimension cell.

| Level | Sonian label | What it means in practice |
|---|---|---|
| **1** | **Ad hoc** | No documented process. Outcomes depend on individual heroics and tribal knowledge. Reactive and unstable. |
| **2** | **Emerging** | Some repeatable practice exists in pockets, usually by application or team. Not enterprise-governed; results vary by who's doing the work. |
| **3** | **Governed** | Documented, standardized, and applied consistently across the data estate with clear ownership. **← MY2029 readiness floor.** |
| **4** | **Measured** | Quality and performance tracked against SLAs; vendor and internal accountability enforced with metrics. |
| **5** | **Self-Sustaining** | Governance embedded and automated; continuous monitoring drives improvement without a project pushing it. |

#### Five Capability Pillars + the Computable Data Governance Overlay

The CDG-MM scores five capability pillars, with Computable Data Governance layered *across* them as an overlay — not as a sixth pillar. Together the five pillars represent roughly **70–80% of the core capability surface of a typical data governance platform** — the entire "understand and trust your data" stack. The one core capability deliberately **out of scope** is access control / security / policy enforcement, which in a payer FHIR architecture belongs to the plan's IAM/security layer, not Sonian's independent validation layer.

1. **Data Inventory & Catalog** — a searchable inventory of data assets, systems, and feeds. *"You cannot manage what you cannot see."*
2. **Metadata Management** — technical + business metadata: definitions, ownership, context, and active propagation of classification tags downstream.
3. **Master & Reference Data Management (MDM)** — consistent, governed definitions of the entities shared across the organization.
4. **Data Quality** — continuous definition, measurement, and remediation of fitness-for-use, on data at rest *and* in flight. At maturity, quality is *computed* — schema/terminology conformance run by an engine, dimension scores derived from PIQI-style rules — not assessed by hand.
5. **Data Lineage & Provenance** — end-to-end traceability from source system through transformation to consumption, ideally at field/column level, with provenance metadata at every hop.

The **Computable Data Governance overlay** expresses how each pillar is governed: decision rights, accountability, policy, and controls, in a **decentralized, catalog-as-single-source-of-truth, governed-at-ingestion** posture (echoing the L.A. Care lesson — govern quality, metadata, and lineage at the earliest and cheapest point to catch error). It is not scored separately at the cell level; instead a single **Governance Index** is *derived* from cells already scored (see below), so the overlay stays intact while still answering "how governed are we?" with one number.

#### Three Assessment Dimensions → the 15-Cell Matrix

Each pillar is scored across three dimensions — a reframing of the classic people/policy/technology lens that *is* the governance overlay made measurable:

- **People & Accountability** — Are roles, stewardship, and decision rights defined and filled? Who is accountable when this pillar fails?
- **Policy & Standards** — Are the rules documented, official, and enforced (not merely written)?
- **Technology & Automation** — How capable and automated is the tooling, and how consistently is it used? At the upper levels this means *computable* instruments — conformance engines and computed quality scores.

**The matrix: 5 pillars × 3 dimensions = 15 scored cells, each rated 1–5 against the ladder.** Governance lives in two of the three dimensions — **People & Accountability** and **Policy & Standards** — which feed the Governance Index. The full Level 1–5 descriptor text for all 15 cells, plus the per-cell guiding questions, is maintained in the standalone **CDG-MM** reference document in the DQAR Shared KB.

#### Payer Calibration — What "Good" Means per Pillar

**Pillar 1 — Inventory & Catalog.** Every upstream vendor feed (EHR, lab, pharmacy, supplemental) and FHIR resource type is registered with a manifest. At maturity, new assets auto-register at onboarding and unregistered feeds cannot enter the pipeline.

**Pillar 2 — Metadata Management.** Does a data catalog (Collibra, Alation, dbt docs) cover HEDIS-relevant assets, and does it reach the FHIR pipeline or only the BI/reporting layer? Are transformation rules documented at field level — `EDW.claim_line.diag_cd_1 ← CAPS.transaction.icd_diag_1`, not "claims flow from CAPS to EDW"? Is there a data dictionary mapping HEDIS data elements to source fields? Without it, semantic-validation findings can't be remediated — the plan doesn't know which upstream field to fix.

**Pillar 3 — MDM.** The three payer master domains that move measure rates:
- *Member MDM* — identity resolution across enrollment sources, retroactive disenrollment handling, product-line transitions. Failures corrupt denominator completeness. Is there a governed member identity matching process connected to HEDIS eligible-population logic? Are enrollment edge cases handled by a governed rule set or ad hoc?
- *Provider MDM* — specialty, network status, TIN-to-NPI mapping, attribution logic. Failures corrupt provider-attributed denominators and clinical data completeness by provider. Is the provider directory governed against NPPES? Is specialty mapping version-controlled?
- *Terminology MDM* — SNOMED, LOINC, RxNorm, NDC bindings governed at platform level or per-application? Is the VSD refresh an annual governed process with a documented owner and change-control record?

**Pillar 4 — Data Quality.** Measured across the nine DQ dimensions (accuracy, semantics, structure, completeness, uniqueness, timeliness, reasonableness, consistency, integrity) and Sonian's five-level semantic validation; quality governed at ingestion, not the warehouse tail. At the top of the ladder, scores are *computed* by engine — schema/terminology conformance and PIQI-style rules — covering data at rest **and** in flight.

**Pillar 5 — Lineage & Provenance.** Field-level lineage carried through to the FHIR surface with AuditEvent provenance — not system-level hand-waving. At maturity, column/field-level lineage is auto-built across sources and reaches the FHIR layer, not just BI.

**The governance overlay in practice.** Is there a data governance function — council, CDO, or equivalent — with authority over data-quality standards across HEDIS-relevant systems, or is governance fragmented by application owner? Are there documented data-quality SLAs for HEDIS-relevant feeds (conformant-LOINC vendor obligations, EHR-feed latency)? Is there a year-round change-control process for ETL rules, value-set bindings, and measure logic? Absence of post-lock change documentation reflects the deeper failure — no year-round change governance. These are precisely the People & Accountability and Policy & Standards questions the Governance Index re-reads across all five pillars.

#### The Governance Index (Derived)

The **Governance Index** is the mean of the two governance dimensions — the ten **People & Accountability** and **Policy & Standards** cells across all five pillars — reported on the same 1–5 scale alongside the five pillar averages.

> **Governance Index** = mean(all 5 People & Accountability scores + all 5 Policy & Standards scores) — one number, 1–5.

Because it re-reads cells already scored rather than adding new questions, it never double-counts, and a plan can read as weakly governed (low index) while still scoring well on a technical pillar like lineage. This lets an assessment say, e.g., *"Governance Index 1.6 — weak decision rights and unenforced policy — while Lineage sits at 3.4"*: the structural root cause and the technical state, side by side. The **Level 3 = MY2029 floor** rule applies to the index too — a Governance Index below 3 is the headline gap for most plans.

#### Scoring, Baseline & Roadmap

Record 1–5 in each of the 15 cells; average each pillar (row) and each dimension (column). The grand picture is a 5×3 heat map, with the two governance columns feeding the Governance Index.

| Pillar | People & Accountability ▓ | Policy & Standards ▓ | Technology & Automation | **Pillar avg** |
|---|---|---|---|---|
| Inventory & Catalog | _ | _ | _ | _ |
| Metadata Management | _ | _ | _ | _ |
| MDM (master/reference) | _ | _ | _ | _ |
| Data Quality | _ | _ | _ | _ |
| Lineage & Provenance | _ | _ | _ | _ |
| **Dimension avg** | _ | _ | _ | |

**Roadmap mechanic.** At baseline, leadership sets a target per pillar **and a target Governance Index** (mix of short/long term). Plot **baseline vs. goal** on a per-pillar scatter, with the Governance Index as its own tracked line; re-score on a set cadence (at least annually for the program; quarterly for the UC2 monitoring subscription) to show the climb. **Level 3 across the board = MY2029 digital-quality readiness floor.** Most plans baseline at 1–2 on MDM and metadata, with a Governance Index of 2–3.

#### Coverage Claim & Clean-Room Provenance (GTM)

**Defensible sales phrasing:** *"The five pillars the CDG-MM scores — inventory/catalog, metadata, master & reference data, data quality, and lineage — cover roughly 70–80% of the core capabilities of a typical data governance platform: the entire 'understand and trust your data' stack. The one core capability we intentionally leave out is access control and security enforcement, which in a payer FHIR architecture belongs to the plan's identity and security layer, not the independent validation layer."* Avoid stating a single hard percentage as fact — the 70–80% is Sonian's own estimate from cross-referencing the published core-capability lists of the major data-governance platforms.

**Clean-room IP / licensing note.** The CDG-MM uses no content or branding from any subscription-gated maturity model (including CMMI-DMM / the CMMI Institute, now merged with ISACA) and no copied third-party assessment text. Some publicly posted maturity assessments carry restrictive licenses (e.g., Creative Commons NonCommercial-NoDerivs) that forbid both commercial use and adaptation and are therefore **not** a permissible base. CDG-MM reuses only uncopyrightable structural ideas — a 1–5 ladder and a capability × dimension grid — with all level descriptors and guiding questions in original Sonian wording. This is what lets Sonian sell and adapt it freely; bodies of knowledge such as DAMA-DMBOK and DGI are used only as *vocabulary the CDO recognizes*. Recommended: have IP counsel confirm before external publication.

**Note:** The full 15-cell CDG-MM descriptor matrix and payer-calibrated readiness survey (one question per cell) live in the standalone CDG-MM reference document. This summary integrates the model's structure, scoring, and GTM framing; the per-cell descriptors are maintained there to avoid drift between the two artifacts.

---

## The Six DQAR Audit Domains

### Domain 1 — IS Assessment
Evaluates payer information system capabilities: system inventory, EDI transaction handling, FHIR server provenance, access controls, and change management. The NCQA IS Assessment accepts narrative descriptions and staff interviews. DQAR requires machine-readable artifacts — a materially higher and more defensible standard.

### Domain 2 — Value Set Conformance and Currency
Highest-yield domain. Most plans have stale value set bindings. Key procedures:
- VSD currency check against NCQA MY2025 (369 value sets, 179,831 codes, 15 code systems)
- NDC Medication List Directory currency
- SNOMED/LOINC/ICD-10 cross-mapping audit (Level 1–3 combined)
- Terminology drift detection (MY2024 → MY2025 retirements)

**VSD conformance template — three modes:**
- Mode 1: API reference — client's Termbox/FHIR terminology server, Sonian read-only scoped access
- Mode 2: Client-provided export — client's licensed VSD loaded to assessment sandbox, deleted at engagement close per SOW
- Mode 3: JSON value sets from client's dQM package — FHIR ValueSet resources included in licensed DCS package, loaded directly to Termbox; covers ECDS measures only; no Excel parsing required

**NCQA DCS JSON value sets:** For ECDS measures, NCQA distributes value sets as JSON FHIR ValueSet resources within the dQM package. As of MY2026, 25 measures are reportable via ECDS across five categories (behavioral health, preventive screening, immunizations, health equity, chronic condition management). Pricing not publicly listed — contact NCQA Account Executive. The dQM Evaluation Package is likely the appropriate tier for assessment/testing purposes.

**MY2026 SSoR removal:** As of MY2026, source system of record (SSoR) reporting is no longer required for ECDS. SSoR data elements have been removed from all ECDS measure data element tables. NCQA is exploring alternative methods to evaluate data source use and establish provenance in alignment with interoperability standards. This simplifies HEDIS reporting and accelerates the digital quality transition — but does not eliminate the need for provenance tracking within a plan's own FHIR pipeline. Plans should maintain internal AuditEvent-based source attribution even as NCQA removes the SSoR submission requirement.

### Domain 3 — Data Lineage Tracing
For each HEDIS measure:
```
source field → transformation rule → intermediate table → analytic field → measure flag
```
Plans without dbt or equivalent lineage tooling cannot produce this documentation. Absence of traceable lineage is itself a material finding.

### Domain 4 — Semantic Validation
The highest unmet demand in the market. Corresponds to Levels 3–4 of the semantic validation framework. Key procedures:
- Code-in-context validation (encounter type constraints)
- Negation and exception code audit
- Clinical plausibility checks
- ECDS data source attribution verification

### Domain 5 — Population Completeness

**PIQI Framework integration:** Domain 5 is operationalized using the PIQI (Patient Information Quality Improvement) framework dimensions. PIQI is explicitly cited in the foundational DQAR article as a required framework for the next-generation audit. The four PIQI dimensions map directly to Domain 5 procedures:

- **Usability** -- 834 enrollment reconciliation. Is the full eligible population present in the FHIR pipeline? Gap between 834 member count and FHIR Patient/Coverage count is a PIQI usability failure.
- **Plausibility** -- Continuous enrollment logic audit. Enrollment periods, gaps, retroactive disenrollment, product-line transitions. Demographic constraint consistency (age, sex, product line) across resources.
- **Comparability** -- Clinical data completeness by provider. Contribution rate consistency across high-volume PCPs. A provider with high attribution and zero clinical records is a PIQI comparability failure -- systematic completeness gap affecting every ECDS measure denominator.
- **Stability** -- Population-level anomaly detection (Level 5). Unexpected shifts in denominator size, exclusion rate, attribution patterns, feed volume per source-feed-id. Implemented via scikit-learn/PyOD (Isolation Forest, DBSCAN, One-Class SVM). Apply per source-feed-id, not globally -- multi-vendor pipelines have different baselines per feed.

**PIQI limitations for DQAR:** Stability checks require per-feed baselines, not global baselines. Comparability checks require concept-level comparison via Termbox value set mapping where multiple code systems represent the same clinical concept across feeds.

### Domain 6 — ECDS and dQM Readiness
Forward-looking domain assessing both current ECDS reporting capability and readiness for digital quality measures (dQMs). **ECDS and dQM are related but not synonymous** — a distinction critical for client positioning:

- **ECDS** is a HEDIS reporting standard — a structured way for health plans to aggregate and submit electronic clinical data for HEDIS quality measurement. It defines what data to collect and how to submit it.
- **dQM (Digital Quality Measure)** is a standard, interoperable, computer-interpretable format for measure specifications — FHIR/CQL-computable measure content. ECDS and traditional HEDIS measures are both available as dQMs through NCQA Digital Content Services. A plan can report ECDS without using dQMs, and can implement dQMs for measures beyond ECDS.

Domain 6 assessment procedures:
- CQL library version verification against NCQA-released dQM packages (Digital Content Services)
- Parallel hybrid/ECDS reconciliation (required for measures still in transition)
- FHIR pipeline completeness by measure against MY2026 ECDS measure set (25 measures)
- Data source attribution by feed across the four ECDS source categories (EHR/PHR, HIE/clinical registry, case management, administrative)
- CQL engine readiness: is the plan's engine certified or validated against NCQA measure packages? Is it plan-controlled or vendor-locked?
- Hybrid retirement gap analysis: for plans still running hybrid measures, identify which of the remaining hybrid measures have planned ECDS equivalents vs. those being retired (WCC) or replaced (PPC)

**CQL engine considerations for Domain 6:** NCQA DCS provides measure logic in FHIR/CQL format. Multiple open-source and commercial CQL engines exist. NCQA does not require a specific engine — it certifies that the measure logic is correct, not that a specific engine is used. Plans should understand whether their engine is plan-owned, vendor-hosted, or licensed — and whether it supports the full MY2026 dQM package. The DQAR assessment surfaces engine dependency as a Tier 3 finding where applicable.

**Related NCQA resources for plans implementing dQMs:**
- [CQL Engines for Technical Teams](https://www.ncqa.org/resources/cql-engines-for-technical-teams/) — NCQA guidance on engine selection and implementation
- [A Practical Guide to Getting Started With Digital Quality Measures](https://www.ncqa.org/resources/a-practical-guide-to-getting-started-with-digital-quality-measures/)
- [The Path to Digital HEDIS](https://www.ncqa.org/resources/the-path-to-digital-hedis/)
- [Digital Quality Hub](https://www.ncqa.org/digital-quality-transition/) — NCQA's central resource for the digital quality transition

---

## Regulatory Timeline

| Milestone | Detail | Source |
|---|---|---|
| MY2023 | Breast Cancer Screening (BCS-E) transitions to ECDS-only | NCQA ECDS Resource Page |
| MY2024 | Colorectal Cancer Screening (COL-E), Follow-Up Care for Children Prescribed ADHD Medication (ADD-E), Metabolic Monitoring for Children and Adolescents on Antipsychotics (APM-E) transition to ECDS-only | NCQA ECDS Resource Page |
| MY2025 | Childhood Immunization Status (CIS-E), Immunizations for Adolescents (IMA-E), Cervical Cancer Screening (CCS-E) transition to ECDS-only; 8 hybrid-method measures still permitted | NCQA ECDS Resource Page |
| MY2026 | Lead Screening in Children (LSC-E), Statin Therapy for Patients with Diabetes (SPD-E), and Statin Therapy for Patients with Cardiovascular Disease (SPC-E) transition to ECDS-only. Three new ECDS measures added: Tobacco Use Screening and Cessation Intervention (TSC-E), Follow-Up After Acute Care Visits for Asthma (AAF-E), Blood Pressure Control for Patients with Diabetes (BPD-E). SSoR reporting requirement eliminated for all ECDS measures. Total ECDS measure set: 25 measures across behavioral health, preventive screening, immunizations, health equity, and chronic condition management. | NCQA ECDS Resource Page (updated Jan 2026) |
| MY2026 | January 2026 NCQA refinements to hybrid transition pathways: Weight Assessment & Counseling (WCC) prioritized for MY2029 retirement (no administrative-only interim); Prenatal and Postpartum Care (PPC) moving to new ECDS/risk-based replacement by MY2028 with concurrent hybrid retirement; Transitions of Care (TRC) and Care for Older Adults (COA) ECDS versions delayed to MY2028, optional until hybrid removed MY2029 | NCQA ECDS Resource Page (Jan 2026 update) |
| MY2028 | New ECDS versions of Transitions of Care (TRC) and Care for Older Adults (COA) introduced for optional reporting; new ECDS/risk-based replacement for Prenatal and Postpartum Care targeted | NCQA ECDS Resource Page |
| MY2029 | All remaining Hybrid-method measures retired. MY2029 endpoint unchanged per January 2026 NCQA announcement. Weight Assessment & Counseling (WCC) retired (replacement measure in development). | NCQA ECDS Resource Page |
| Jan 1, 2027 | CMS-0057-F: Patient Access, Provider Access, Payer-to-Payer APIs required | CMS Final Rule |

### Hybrid Retirement Calendar — Measure-by-Measure Status (as of January 2026)

Eight HEDIS measures still permitted Hybrid reporting as of MY2025. The table below reflects the updated pathways announced by NCQA in January 2026.

| Measure | Hybrid Retirement | ECDS Equivalent | Pathway Notes |
|---|---|---|---|
| Weight Assessment and Counseling for Nutrition and Physical Activity for Children/Adolescents (WCC) | MY2029 (retirement) | None planned | No administrative-only interim. NCQA prioritizing measure retirement; replacement measure in development. |
| Prenatal and Postpartum Care (PPC) | MY2028 (concurrent with new measure) | New ECDS/risk-based replacement measure | Development of replacement measure targeted for MY2028; hybrid retired concurrently. No direct PPC-E equivalent — new measure replaces, not mirrors, hybrid. |
| Transitions of Care (TRC) | MY2029 | TRC-E (optional MY2028–MY2028) | ECDS version introduction delayed to MY2028. Optional reporting MY2028–MY2028; hybrid removed MY2029. |
| Care for Older Adults (COA) | MY2029 | COA-E (optional MY2028) | Same pathway as TRC. ECDS version delayed to MY2028; optional until hybrid retired MY2029. |
| *Additional hybrid measures (up to 4 others as of MY2025)* | MY2029 | Varies | Some transition to direct ECDS; others may follow develop-test-retire pathway. Confirm measure-specific pathways against current NCQA Vol. 2 each measurement period. |

**Key principle:** Not all hybrid measures have a direct ECDS equivalent. WCC has no planned ECDS counterpart — it will be retired. PPC will be replaced by a new measure, not ported to ECDS. For TRC and COA, the ECDS versions are new parallel measures that will coexist with hybrid until MY2029 retirement.

**Transition process (per NCQA):** For each measure: (1) develop and test the new ECDS measure; (2) run parallel reporting alongside hybrid to compare results and validate; (3) introduce ECDS measure as optional in HEDIS; (4) retire hybrid after successful implementation. NCQA evaluates data during transition to confirm quality standards are met, provides benchmark guidance, and collaborates with standards organizations to close digital feasibility gaps.

---

## AuditEvent Provenance Architecture

### The Seven-Extension Provenance Pattern
Extend the standard FHIR AuditEvent at ingest time with seven extensions, written once per resource, at write time, by the pipeline. Extensions 1–5 are produced by the **source-type inference algorithm** (it reads US Core MUST SUPPORT signals where it can and falls back through a priority ladder otherwise); extensions 6–7 are set by the pipeline orchestrator at run time.

```json
"extension": [
  { "url": "http://Sonian.io/fhir/ext/source-type", "valueCode": "clinical_ehr" },
  { "url": "http://Sonian.io/fhir/ext/source-system-id", "valueString": "epic-prod-org-447" },
  { "url": "http://Sonian.io/fhir/ext/source-feed-id", "valueString": "ehr-epic-447-clinical" },
  { "url": "http://Sonian.io/fhir/ext/source-inference-confidence", "valueCode": "asserted" },
  { "url": "http://Sonian.io/fhir/ext/ecds-ssor", "valueCode": "EHR/PHR" },
  { "url": "http://Sonian.io/fhir/ext/ingest-pipeline-id", "valueString": "interbox-job-20251014-ehr-001" },
  { "url": "http://Sonian.io/fhir/ext/ol-run-id", "valueString": "a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d" }
]
```

| EXT | Field | Set by | Notes |
|---|---|---|---|
| 1 | `source-type` | inference algorithm | Expanded vocabulary (see below) |
| 2 | `source-system-id` | inference algorithm | Canonical source identifier (e.g., `epic-prod-org-447`) |
| 3 | `source-feed-id` | inference algorithm | Per-feed identifier; `undeclared-*` when not in the manifest |
| 4 | `source-inference-confidence` | inference algorithm | `asserted` / `high` / `low` / `unknown` |
| 5 | `ecds-ssor` | inference algorithm | Derived from `source-type` by the deterministic SSoR mapping rule |
| 6 | `ingest-pipeline-id` | orchestrator | Ingest job identifier |
| 7 | `ol-run-id` | orchestrator | OpenLineage RunEvent UUID — an ingest batch tag, **not** a join key |

**Source-type vocabulary (expanded).** The old four-value declaration (`ecds-ehr` / `ecds-administrative` / `ecds-lab` / `ecds-pharmacy`) is replaced by a richer vocabulary split into two tiers:
- **Tier A — structurally detectable** (inference can resolve without a manifest): `clinical_ehr`, `administrative_claims`, `administrative_encounter`, `pharmacy_pbm`, `clinical_lab` (a US Core `Observation.category` declaration, not a guess), `payer_exchange`, `clinical_immunization_registry`.
- **Tier B — manifest / `meta.source` declared only** (structurally indistinguishable from `clinical_ehr`): `clinical_phr`, `pharmacy_specialty`, `clinical_hie`, `clinical_registry`, `case_management`, `disease_management`.

A Tier B type that defaults to `unknown` because it is neither in the feed manifest nor carries a `meta.source` URI is itself a **Tier 1 governance finding** — the algorithm's limitation *is* the evidence of a metadata-management gap. (Full priority ladder and code in `dqar-05-source-inference-algorithm.md`.)

**SSoR mapping (EXT 5).** `ecds-ssor` is derived from `source-type` by a deterministic rule into the four NCQA ECDS SSoR categories — **EHR/PHR**, **Administrative**, **Clinical Registry/HIE**, **Case/Disease Mgmt** — or `null` for `unknown` (which triggers the finding). Note: although NCQA removed the SSoR *submission* requirement for ECDS as of MY2026, the plan still benefits from internal SSoR attribution for provenance and risk stratification.

**Provenance confidence as a maturity metric (EXT 4).** The distribution of resources across confidence tiers is a direct provenance-maturity score requiring no extra testing: >80% `asserted` reads as Governed (no finding); 50–80% high+asserted as Adequate (Tier 3 advisory); <50% high+asserted as inference-dependent (Tier 3 finding); >20% `unknown` as a material gap (Tier 3 HIGH severity, MY2029 risk).

**Lineage join (EXT 7).** `ol-run-id` tags each resource with the OpenLineage RunEvent that produced it. **RunEvents are emitted directly to OpenMetadata (Marquez has been dropped)**, which builds the lineage graph from each RunEvent's declared inputs and outputs. `ol-run-id` is an ingest batch tag, not a foreign key — the graph is assembled in OpenMetadata, not by joining on this value. Valid `ol-run-id` coverage that resolves in the OpenLineage graph is required for DQAR provenance-maturity Level 3+.

### Measure Attribution Join
```
member flag → resource ID → AuditEvent.entity.reference → ecds-ssor + source-system-id + source-feed-id
```

The seven-extension metadata also makes Domain 3 risk stratification a single SQL-on-FHIR query against the ingest metadata — per `source-system-id`/`source-feed-id`: resource counts, source types, SSoR categories, and which measures they feed — instead of a multi-day manual reconstruction from ETL documentation. That contrast is a concrete demonstration of the Sonian/Health Samurai infrastructure advantage over an incumbent vendor that never exposes this metadata to the plan.

### What AuditEvent Logging Is and Is Not
- ✅ Closes HIPAA audit control gap (45 CFR §164.312(b))
- ✅ Establishes FHIR server transaction log baseline
- ✅ Provides write-time source attribution (inferred or asserted) for ingest pipeline resources
- ✅ Enables automated risk stratification by source feed — no manual inventory reconstruction
- ✅ Confidence tier and `unknown`-rate are computed provenance-maturity metrics
- ❌ Not a current CMS or NCQA mandate
- ❌ Does not automatically provide measure-level execution provenance
- ❌ Does not cover resources created outside the managed ingest pipeline
- ❌ Cannot distinguish Tier B source types without a feed manifest or `meta.source` — undeclared Tier B data defaults to `unknown`

**Regulatory status:** No specific CMS or NCQA mandate requires AuditEvent logging today. Position as Digital Readiness Gap (Tier 3), not Governance Gap (Tier 1).

---

### Upstream Migration of AuditEvent Metadata — The Advisory Opportunity

The DQAR sandbox demonstrates AuditEvent metadata capture at Aidbox ingest time (Stage 5 of the UC1 pipeline). This is the starting point — not the end state.

**The advisory insight:** With Sonian guidance, and using the Aidbox AuditEvent ingest demo as proof of concept, plans can migrate the metadata capture point progressively upstream — from the Sonian sandbox to the plan's own FHIR infrastructure, and ultimately to the plan's FHIR vendor API bulk ingestion point. This means:

```
Stage 1 (demo / Rung 2):
  Sonian Aidbox sandbox captures AuditEvent metadata
  at anonymized extract load time
  → Proves the pattern, demonstrates the SQL risk stratification query

Stage 2 (Rung 3 — plan's own Aidbox):
  Plan's Aidbox instance captures AuditEvent metadata
  at production ingest time
  → Lineage metadata lives in the plan's own infrastructure
  → Risk stratification runs against production data, not a sandbox copy

Stage 3 (Rung 4 — upstream to FHIR vendor API):
  AuditEvent metadata captured at the plan's Bulk FHIR
  $export / ingest API boundary — the earliest possible point
  → Every resource tagged with source-system-id and source-type
    before it ever reaches the measure calculation layer
  → Lineage is native to the pipeline, not retrofitted
  → Upstream errors caught earliest — lowest remediation cost
```

The upstream migration path is an Sonian advisory deliverable — it is not something Health Samurai sells directly, and it is not something a plan's internal team can navigate without guidance on the AuditEvent extension pattern and the FHIR Bulk Data API interaction points. This is a concrete, multi-engagement advisory thread that grows naturally from the UC1 sandbox demonstration.

---

### Velox Metadata Integration — Data Source Inventory Push/Pull

The AuditEvent seven-extension metadata captured at ingest has a natural integration point with the Velox data source inventory. Velox's platform-side view of a plan's data sources is more useful when it reflects the actual per-feed resource counts, source types, and ECDS SSoR categories that the AuditEvent metadata tracks.

**Two integration directions are viable:**

**Push — Aidbox → Velox:**
After each ingest run, a lightweight export of the AuditEvent metadata summary (per `source-system-id`/`source-feed-id`: resource type counts, source type distribution, `ecds-ssor` breakdown, and confidence-tier mix) is pushed to the Velox data source inventory. Velox business users see a live, queryable inventory of what's in the FHIR pipeline — attributed by feed — without needing SQL access to Aidbox.

```
Aidbox AuditEvent metadata (per feed summary)
    → scheduled export job
        → Velox data source inventory API
            → Velox business user dashboard: "EHR feed epic-prod-org-447
               contributed 142,847 Condition resources tagged clinical_ehr
               (SSoR: EHR/PHR), last updated 2025-10-14"
```

**Pull — Velox → Aidbox:**
Velox's existing data source inventory (which the plan may already maintain for other purposes) is used to pre-populate the feed manifest at UC1 engagement kickoff. Rather than constructing the feed manifest from scratch via interviews, Sonian pulls the Velox inventory as the starting point and validates/enriches it against the AuditEvent metadata after ingest.

```
Velox data source inventory
    → feed manifest draft (Sonian kickoff)
        → validated and enriched by AuditEvent metadata post-ingest
            → gap between Velox inventory and actual AuditEvent feeds
              = undeclared source finding (Domain 1 / Domain 3)
```

**The partnership value:** This integration makes the Velox inventory self-correcting over time — it reflects what is actually flowing through the FHIR pipeline, not just what was documented in a spreadsheet during the last IS assessment. For Velox, this is a concrete differentiator: their data source inventory is live and pipeline-sourced, not static. For Sonian, the Velox inventory becomes a pre-populated starting point for every new engagement — reducing kickoff effort and surfacing undeclared sources faster.

**Confirm with Velox:** API availability for data source inventory write (push path) and read (pull path). Priority integration to propose in partnership discussions.

---

## Industry Dialogue — Semantic Validation

**LinkedIn exchange with Jeff Helman (AEGIS), June 2026:**

Michael E. Campbell: *"Clearly Layers 1 and 2 can be validated against base FHIR or IG schemas. Do you envision the same approach for 3 and 4 (i.e., the national or state agency or organization creates an IG specific to their requirements) for conformance validation? Is there a better way than making more IGs?"*

Jeff Helman response: AEGIS directly supports and validates all FHIR IGs named in the CMS-0057-F Final Rule. This confirms IG-based validation covers the regulatory compliance surface (Levels 1–2) but not the measure-specific semantic layer (Levels 3–5). The "better way than making more IGs" answer DQAR proposes: computable data quality rules implemented at multiple lineage checkpoints.

Michael E. Campbell follow-up: *"This is a critical opportunity to implement layered computable data quality validations on multiple points of the data lineage. In my opinion, an under-appreciated feature of open source standards like FHIR is that it establishes a shared but [truncated — retrieve full text]."*

**Note:** Retrieve full text of truncated reply and add here. This is a primary source articulation of the DQAR thesis in industry dialogue.

---

## Industry Case Study — UCare Collapse (2025)

**Source:** John Hoff, MTR Group, LinkedIn, June 2026. "The UCare Collapse Was Fully Visible Before It Happened."

UCare (Minnesota) absorbed a ~20% enrollment increase of displaced UnitedHealthcare/Humana members during AEP 2024 network disruption. The receiving plan had inadequate risk data on the transitioning population. 2025 results: MA loss $263M, Medicaid loss $315M, total $504M. Reserves exhausted.

**Tom Shankle's observation (Healthcare Strategy and Operations):** If the CMS-0057-F Payer-to-Payer data exchange mandate had been in place in 2024, UCare would have received five years of clinical history on those transitioning members — potentially changing the risk assessment and avoiding the financial collapse.

**Michael E. Campbell's reply:** *"Any strategic advantage on payer to payer exchange depends on several data concerns. How complete is the payer data — most clinical data is left out of FHIR by default and most plans don't use FHIR data for analytics. It's still treated as a data source incompatible with legacy analytic platforms. A plan with FHIR native architecture, broad scope of included data, and SQL on FHIR or similar analytic environments can leverage that data while others leave it siloed."*

**DQAR implication for UC5:** The UCare case is the concrete financial consequence of P2P data quality failure. The data was theoretically available. The capability to assess and use it was not. UC5 (Payer-to-Payer Data Exchange Quality) addresses exactly this gap: assessing whether incoming P2P data is complete, semantically valid, and analytically usable — before it enters the risk and quality pipelines.

**Pitch for UC5:** *"UCare received an enrollment cascade they couldn't risk-assess because their analytics infrastructure couldn't leverage the clinical data that was theoretically available. A plan with FHIR-native architecture, governed P2P data quality assessment, and SQL on FHIR analytics turns that data into a competitive advantage. Without it, five years of clinical history on transitioning members sits siloed and unused while the losses accumulate."*

---

## The Incumbent HEDIS Vendor Trap — Strategic Competitive Context

This is one of the most important conversations in a DQAR engagement. Many plans are seriously considering staying with their existing HEDIS vendor — Inovalon, Cotiviti, Arcadia, or equivalent — rather than building toward FHIR-native infrastructure. The DQAR assessment creates a natural decision point, and Sonian must be prepared to make the case clearly.

### What Incumbents Are Offering Now

The major HEDIS ETL and measure reporting vendors have responded to the MY2029 ECDS mandate by adding digital quality reporting engines to their existing platforms. The pitch to plans is: *"You don't have to change anything. We'll handle the FHIR layer for you, just as we handled your ETL."*

This sounds low-risk. It is not.

### The Hidden Cost Structure of Staying

**1. ETL and MRR fees continue — possibly increase**

Plans using Inovalon, Cotiviti, or similar vendors pay for:
- Annual ETL customization to accommodate NCQA measurement period changes
- Measure rate reporting (MRR) production and submission services
- Medical record retrieval (MRR) coordination and chase workflows
- Chart abstraction and hybrid oversample management

These fees are typically $2–6M+ annually for a mid-sized MA or commercial plan. Adding a digital reporting engine on top does not replace this cost structure — it adds to it. The vendor gains a new revenue stream on the ECDS migration while the legacy services remain billable.

Critically: **each HEDIS measure run is a vendor-billed event.** Plans pay per run — for validation runs, parallel testing runs, remediation verification runs, and the final submission run. Running HEDIS measures internally against a plan-owned Aidbox instance with SQL on FHIR queries has no per-run cost beyond infrastructure. The per-run fee model is one of the most underappreciated cost drivers in the incumbent vendor relationship, and one of the clearest ROI arguments for the in-house path.

**2. Lineage visibility disappears at the vendor ETL handoff**

When a plan's data crosses into the HEDIS vendor's ETL pipeline, the plan loses visibility and control. Every transformation hop from that point forward — source normalization, code mapping, measure logic application, ISR/IDR production — happens inside the vendor's black box. The plan receives outputs. It does not receive lineage.

This means:
- The plan cannot trace a member's measure flag back to its originating source record through the vendor's transformations
- When a measure rate changes unexpectedly, the plan cannot determine whether the change originated in their source data or in the vendor's ETL logic
- The vendor's change control process is opaque — undocumented ETL changes after measure lock are a known audit risk that the plan cannot independently monitor
- DQAR Domain 3 (data lineage) findings are the plan's liability, but the evidence lives at the vendor

In contrast, the Sonian + Health Samurai architecture instruments lineage at every hop — from source system through Interbox integration through Aidbox ingest with AuditEvent metadata. The plan owns every lineage artifact. The risk stratification matrix is a query, not a vendor inquiry.

**3. CQL engine lock-in by stealth**

Incumbent vendors bundle their proprietary CQL execution engine with their digital reporting service. The plan's FHIR data becomes queryable only through that vendor's measure packages. When Medical Society measures arrive — or when the plan wants to run population health analytics beyond HEDIS — they have no pathway. The CQL engine the vendor controls becomes the bottleneck for every future quality use case.

**4. No independent auditability**

When the HEDIS vendor both produces the data and runs the measure calculation, there is no independent verification layer. NCQA DCS explicitly disclaims data mapping validation. The vendor's quality engine certifies itself. This is the same structural conflict of interest that exists in the certified auditor relationship — the plan has no independent view of whether their measure rates are defensible.

### What In-House FHIR with Sonian + Health Samurai Provides Instead

| Dimension | Incumbent HEDIS vendor | Sonian + Health Samurai path |
|---|---|---|
| FHIR infrastructure ownership | Vendor-hosted, plan has limited access | Plan-owned or plan-controlled Aidbox instance |
| ETL costs | Annual recurring, often opaque pricing | One-time implementation, plan-controlled thereafter |
| Per-HEDIS-run cost | Billed per run — validation, parallel testing, remediation, submission all cost | No per-run cost against plan-owned infrastructure |
| Measure reporting | Vendor produces ISR/IDR | Plan runs SQL on FHIR queries; Sonian validates |
| Data lineage visibility | Terminates at vendor ETL handoff — plan cannot trace beyond that boundary | End-to-end lineage from source system through Aidbox ingest; AuditEvent metadata at every hop |
| Lineage traceability point | Downstream of vendor ETL — too late for early error detection | Moves upstream to plan's own FHIR API bulk ingestion point with Sonian advisory |
| CQL engine | Vendor-proprietary, locked | Engine-agnostic; plan points data at any FHIR-capable CQL runtime |
| Data governance | Vendor-managed, plan visibility limited | Plan-owned; Sonian assesses and advises governance maturity |
| Independent validation | None — vendor validates itself | DQAR assessment provides independent semantic validation layer |
| Medical Society measures | Dependent on vendor roadmap | Plan can adopt any new CQL measure package independently |
| Long-term cost trajectory | Increases with measure complexity and run volume | Decreases as plan matures toward in-house capability |
| P2P exchange readiness | Vendor handles ingest — quality unknown | UC3 assessment validates incoming data before it enters the pipeline |

### The DQAR Assessment as a Migration Decision Tool

The DQAR UC1 assessment is structured to produce exactly the evidence a CDO needs to make this build-vs-buy decision:

- **Tier 3 findings** (Digital Readiness Gaps) document what the current vendor's FHIR implementation is missing — AuditEvent logging, US Core conformance, provenance metadata. These findings quantify the governance debt the plan is accumulating by staying.
- **Level 6 governance assessment** documents where plan-side capability currently sits. If the plan has no internal FHIR engineering capability, the roadmap names what must be built and in what sequence.
- **The remediation roadmap** provides a sequenced migration path away from incumbent vendor dependency, timed against MY2029 milestones and the Jan 1, 2027 P2P deadline.

**The pitch to a plan considering staying with Inovalon or Cotiviti:**

*"Your vendor is offering to manage your FHIR migration — which means your FHIR infrastructure, your data governance, and your CQL engine will live at the vendor, not at your plan. You will pay ETL fees and MRR fees and now a digital reporting fee, and you will have less visibility into your own data than you have today. A DQAR assessment costs a fraction of one year's vendor fees and tells you exactly what you need to build to own your own pipeline. The Health Samurai implementation that follows is a one-time investment in infrastructure you control. At $4K/month for ongoing advisory, you replace a multimillion-dollar annual vendor dependency with a cost-effective alternative that gives you more control, better reporting, higher QA efficiency, and a platform that can handle Medical Society measures, P2P exchange quality, and anything else that arrives after MY2029."*

### Target Replacement Path

The DQAR assessment creates a qualified target implementation path:

```
Current state:    Inovalon / Cotiviti ETL + MRR + (new) digital reporting engine
                      ↓  UC1 assessment identifies gaps and migration requirements
Transition:       Aidbox (Health Samurai) as plan-controlled FHIR server
                  Termbox for value set governance
                  Interbox for HL7v2/C-CDA integration pipeline
                  Velox for business user quality dashboard (plan-side)
                  Sonian for ongoing assessment objectivity and advisory
                      ↓  UC2 monitoring subscription through the migration
Target state:     Plan-owned FHIR infrastructure
                  Engine-agnostic CQL measure execution
                  Independent DQAR validation layer
                  Full P2P exchange readiness (UC3)
                  Medical Society measure-ready
```

---

## CQL Engine Agnosticism and Medical Society Measures

### DQAR Is Measure-Framework Agnostic

The DQAR five-level semantic validation methodology applies to any CQL-based measure consuming FHIR data. The five levels — terminology conformance, structural conformance, context conformance, clinical plausibility, population completeness — are requirements of the data, not of any specific measure framework. HEDIS is the initial focus because it has the regulatory urgency and the largest financial stakes. The methodology generalizes to any quality measure that executes against a FHIR data store.

This is a significant long-term positioning statement: as Medical Society measures proliferate, Sonian is already positioned to assess readiness for them without framework-specific customization.

### The Medical Society Measure Landscape

The AMA, ACC (cardiology), ACS (oncology), ASN (nephrology), and other specialty societies are actively developing FHIR/CQL-based clinical quality measures outside the NCQA HEDIS framework. CMS is incorporating specialty society measures into value-based care contracts, and MA quality frameworks are likely to follow.

For payers, this creates a structural problem that the incumbent vendor model cannot solve:

- Each society publishes its own CQL library with its own value sets (typically through VSAC but with independent governance cycles)
- Profile constraints may differ from HEDIS QI Core profiles
- Measure update cadences do not align with the NCQA measurement period calendar
- Plans cannot wait for incumbent vendors to add support — competitive advantage accrues to plans that can adopt new measures early

### Engine-Agnostic Architecture Enables Multi-Measure Execution

A plan with a well-governed FHIR server (Aidbox or otherwise) can point their data at multiple CQL engines simultaneously:

```
FHIR Data Store (plan-owned Aidbox)
    ├── NCQA HEDIS dQMs      → NCQA-certified CQL engine or SQL on FHIR
    ├── ACC cardiology        → ACC CQL library → any FHIR-capable CQL runtime
    ├── ACS oncology          → ACS CQL library → same or different runtime
    ├── CMS value-based care  → CMS CQL packages → plan's preferred runtime
    └── Plan-custom measures  → plan-built SQL on FHIR ViewDefinitions
```

The FHIR server is the single source of truth. CQL engines are consumers. This decoupling is only possible when the plan owns the FHIR infrastructure — not when it lives at a HEDIS vendor.

**The DQAR implication:** The UC2 monitoring subscription naturally extends to cover Medical Society measure conformance as those libraries mature. The same five-level validation methodology applies — just pointed at different value sets and profile constraints. Termbox's hybrid terminology architecture (local resolver for custom/HEDIS value sets, delegation to VSAC/NLM for standard terminologies) handles the multi-framework value set governance problem natively.

### What Plans Should Ask Their HEDIS Vendor Right Now

A DQAR engagement arms the plan's CDO with the right questions:

1. *"When ACC publishes their cardiology CQL library, how quickly can we run it against our data? What does that cost?"*
2. *"Can we query our FHIR data directly with our own SQL tools, independent of your reporting engine?"*
3. *"What is your upgrade path when NCQA changes US Core profile requirements between MY2025 and MY2029?"*
4. *"Who owns the AuditEvent provenance metadata on our FHIR resources — us or you?"*
5. *"When the P2P exchange goes live in January, who validates that incoming data before it enters our pipeline?"*

No incumbent HEDIS vendor has satisfactory answers to all five. The DQAR assessment surfaces exactly these gaps and provides the roadmap to address them.

---

## Industry Pain Points (Strategic Context)

- Annual HEDIS reporting requires "redundant, idiosyncratic, annual hard coding" of measures and manual chart abstractions
- CAQH estimates shifting from manual to automated quality workflows could save payers and providers ~$20 billion annually
- Health plans choose and pay their own certified auditor — structural conflict of interest analogous to pre-Sarbanes-Oxley corporate auditing
- Plans eager for anything that makes their data defensible before an auditor arrives
- Direct public criticism of HEDIS auditors suppressed by regulatory stakes (star ratings, CMS bonuses)
- NCQA DCS explicitly disclaims data mapping and accuracy validation — the upstream gap is unowned and unaddressed in the current vendor landscape
- **Incumbent HEDIS vendors are adding digital reporting engines that reproduce vendor dependency in FHIR clothing — plans risk paying more for less control**
- **CQL engine lock-in by incumbent vendors blocks Medical Society measure adoption and limits analytics independence**
- **Plans without in-house FHIR infrastructure cannot independently validate their own measure rates or P2P exchange data quality**
