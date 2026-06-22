# Phase 4: Integration with dqar-client-kit (Weeks 7–8)

> **The two kits never call each other at runtime.** They integrate through
> **artifacts**: client-kit *generates* `uc-properties.json` + findings;
> aidbox-databricks-kit *loads* properties (Phase 1) and *emits* provenance
> (Phases 2–3). This phase defines that contract and the consistency checks that
> keep the three identity linkages from drifting.

---

## The Boundary

```
dqar-client-kit                         dqar-aidbox-databricks-kit
───────────────                         ──────────────────────────
reads NDJSON extract                    runs at ingest time (Aidbox/Interbox)
matches to manifest                     writes AuditEvent EXT 6 + 7  (Phase 3)
runs 5-level conformance                emits OpenLineage RunEvent   (Phase 2)
GENERATES uc-properties.json  ───────►  LOADS uc-properties.json     (Phase 1)
GENERATES findings (tiers 1–3)          (no value computation here)
```

Client-kit is **assessment-time** (post-hoc, reads an extract). This kit is
**ingest-time** (writes provenance as data lands). They meet at two artifacts: the
UC properties document and the shared identity values.

---

## Shared Contract Types (from `dqar-contracts`)

Both kits depend on `dqar-contracts>=1.0.0,<2.0.0` and re-export from
`dqar_contracts.shared` via the `shared/engagement.py` shim. Neither kit redefines
these — that's the whole point of the contracts package.

- `Engagement`, `OrganizationRef`, `MeasurementPeriod`
- `MeasureId`, `MeasureSpec`, `ViewDefinitionRef`

If a type needs to change, it changes in `dqar-contracts` with a version bump — not
locally in either kit.

---

## The Three Identity Linkages (must stay consistent)

These are the load-bearing joins across the system. Each is a place where the two
kits' outputs must agree; disagreement is a **finding**, not a warning.

| # | Linkage | client-kit side | aidbox-databricks side |
|---|---|---|---|
| 1 | **Run identity** | `dqar_lineage_ol_run_id` (UC property) | AuditEvent EXT 7 `ol-run-id` == RunEvent `runId` |
| 2 | **Feed attribution** | `dqar_source_feed_id` (UC property) | `DQARIngestFacet.sourceFeedId` |
| 3 | **Per-resource ↔ per-table** | per-table UC summary | per-resource AuditEvent run identity |

```
Linkage 1:  AuditEvent.EXT7  ==  RunEvent.runId  ==  UC.dqar_lineage_ol_run_id
Linkage 2:  UC.dqar_source_feed_id  ==  DQARIngestFacet.sourceFeedId
Linkage 3:  per-resource AuditEvent run  rolls up to  per-table UC attribution
```

---

## Integration Validator

`aidbox_databricks/integration/consistency_validator.py` — run after a batch is
ingested and its UC properties are loaded.

```python
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ConsistencyFinding:
    linkage: int            # 1, 2, or 3
    severity: str           # "tier_1" | "tier_2"
    detail: str


@dataclass
class ConsistencyReport:
    findings: list[ConsistencyFinding] = field(default_factory=list)
    @property
    def consistent(self) -> bool:
        return not self.findings


class ConsistencyValidator:
    """Checks the three identity linkages between the two kits' outputs."""

    def validate(self, *, uc_properties: dict, audit_events: list[dict],
                 run_event: dict) -> ConsistencyReport:
        report = ConsistencyReport()

        # Linkage 1: EXT7 == RunEvent.runId == UC.dqar_lineage_ol_run_id
        run_id = run_event["run"]["runId"]
        uc_run_id = uc_properties["properties"].get("dqar_lineage_ol_run_id")
        if uc_run_id and uc_run_id != run_id:
            report.findings.append(ConsistencyFinding(
                1, "tier_1",
                f"UC dqar_lineage_ol_run_id {uc_run_id} != RunEvent.runId {run_id}"))
        for ae in audit_events:
            ext7 = _ext_value(ae, "ol-run-id")
            if ext7 and ext7 != run_id:
                report.findings.append(ConsistencyFinding(
                    1, "tier_1",
                    f"AuditEvent EXT7 {ext7} != RunEvent.runId {run_id}"))

        # Linkage 2: UC.dqar_source_feed_id == DQARIngestFacet.sourceFeedId
        uc_feed = uc_properties["properties"].get("dqar_source_feed_id")
        facet = _dqar_ingest_facet(run_event)
        if facet and uc_feed and facet.get("sourceFeedId") != uc_feed:
            report.findings.append(ConsistencyFinding(
                2, "tier_2",
                f"facet.sourceFeedId {facet.get('sourceFeedId')} != UC {uc_feed}"))

        # Linkage 3: every resource's AuditEvent carries the batch run identity
        for ae in audit_events:
            if not _ext_value(ae, "ol-run-id"):
                report.findings.append(ConsistencyFinding(
                    3, "tier_2",
                    f"AuditEvent {ae.get('id')} missing EXT7 ol-run-id"))

        return report
```

`_ext_value`, `_dqar_ingest_facet` are small helpers that read the extension by URL
suffix and pull the facet off the RunEvent output. The validator returns findings;
it does not raise — surfacing a finding is the product behavior.

---

## What This Phase Does NOT Do

- **Does not run conformance.** That's client-kit. This kit consumes the *result*
  (UC properties) and checks it against ingest-time provenance.
- **Does not generate UC property values.** Phase 1 loads them as-is.
- **Does not re-implement manifest matching.** Undeclared feeds surface as
  `UNKNOWN` in client-kit's matching → Tier 1 finding there. This kit doesn't infer.

---

## Phase 4 Success Criteria

- [ ] Both kits import shared types from `dqar-contracts` (no local redefinition)
- [ ] `ConsistencyValidator` checks all three identity linkages
- [ ] Linkage 1 mismatch (run identity) → Tier 1 finding
- [ ] Linkage 2 mismatch (feed attribution) → Tier 2 finding
- [ ] Linkage 3 gap (resource missing EXT 7) → Tier 2 finding
- [ ] Validator returns findings, does not raise
- [ ] No conformance logic, no UC value computation, no source inference in this kit
