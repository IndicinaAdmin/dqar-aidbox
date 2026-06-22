# Phase 5: Integration & Orchestration (Weeks 9–10)

> Ties Phases 1–4 into a single ingest run: open a lineage run, write atomic
> resource+AuditEvent bundles, emit the RunEvent with the `DQARIngestFacet`, load
> UC properties, and validate the three identity linkages. This is the order of
> operations that keeps EXT 6/7, the RunEvent, and the UC properties in agreement.

---

## Deliverables

1. **IngestOrchestrator** (`aidbox_databricks/orchestration/orchestrator.py`)
   - Drives the full sequence; owns the `IngestContext`
2. **IngestContext** (`aidbox_databricks/orchestration/context.py`)
   - Carries `ingest_pipeline_id` (EXT 6), `ol_run_id` (EXT 7), `source_feed_id`, `source_system_id` through the run
3. **CLI entry** (`aidbox_databricks/cli.py`)
   - `aidbox-dqar ingest --feed <id> --bundle <ndjson> [--load-uc-props uc-properties.json]`
4. **End-to-end test** (`tests/test_orchestration_e2e.py`)
   - Full happy path + one consistency-failure path

---

## Orchestration Sequence (the canonical order)

```
1. start_run()                         → ol_run_id            [Phase 2]
2. build IngestContext(
     ingest_pipeline_id, ol_run_id,
     source_feed_id, source_system_id)
3. for each resource in batch:
     POST atomic transaction bundle     [Phase 3]
       { resource , AuditEvent(EXT6=pipeline_id, EXT7=ol_run_id) }
4. complete_run(outputs + DQARIngestFacet)  [Phase 2]
5. (if uc-properties.json provided)
     UCPropertiesLoader.load_from_json()    [Phase 1]
6. ConsistencyValidator.validate(           [Phase 4]
     uc_properties, audit_events, run_event)
7. emit ConsistencyReport (findings, if any)
```

Order matters: the `ol_run_id` from step 1 must exist before step 3 writes it into
every AuditEvent's EXT 7, and before step 4 emits it as the RunEvent `runId`. If
step 3 or 4 fails, call `fail_run()` — never leave a START unterminated.

---

## IngestContext

```python
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class IngestContext:
    ingest_pipeline_id: str   # → AuditEvent EXT 6
    ol_run_id: str            # → AuditEvent EXT 7 == RunEvent.runId
    source_feed_id: str       # → DQARIngestFacet.sourceFeedId, UC dqar_source_feed_id
    source_system_id: str
    measurement_period: str
```

One immutable context per batch, threaded through every step so the same four
identifiers reach the bundle writer, the emitter, and the validator. This is what
prevents the three linkages from drifting — they all read from one source.

---

## Orchestrator Sketch

```python
class IngestOrchestrator:
    def __init__(self, emitter, bundle_writer, uc_loader, validator):
        self._emitter = emitter
        self._writer = bundle_writer
        self._uc_loader = uc_loader
        self._validator = validator

    def run(self, *, feed_id, system_id, pipeline_id, measurement_period,
            resources, inputs, uc_properties_path=None):
        run_id = self._emitter.start_run(
            job_namespace="interbox", job_name=f"ingest-{feed_id}", inputs=inputs)
        ctx = IngestContext(pipeline_id, run_id, feed_id, system_id, measurement_period)
        audit_events = []
        try:
            for resource in resources:
                ae = self._writer.write_atomic(resource, ctx)   # Phase 3 bundle POST
                audit_events.append(ae)
            run_event = self._emitter.complete_run(
                run_id, "interbox", f"ingest-{feed_id}",
                outputs=self._writer.outputs_with_facet(ctx))
        except Exception as e:
            self._emitter.fail_run(run_id, "interbox", f"ingest-{feed_id}", str(e))
            raise

        if uc_properties_path:
            self._uc_loader.load_from_json(uc_properties_path)   # Phase 1

        report = self._validator.validate(                       # Phase 4
            uc_properties=_props_for(feed_id, uc_properties_path),
            audit_events=audit_events,
            run_event=run_event)
        return report
```

---

## Atomicity Reminder (Phase 3 invariant carried here)

Each resource and its AuditEvent are written as **one** FHIR transaction bundle
(`type: "transaction"`, not `batch`): the AuditEvent's `entity.what.reference` uses
the same `urn:uuid:` placeholder as the resource's `fullUrl`. Aidbox's atomicity
guarantee applies only within a single bundle POST — so the orchestrator must not
split the pair across calls. A resource landing without its AuditEvent (or vice
versa) is exactly the failure this invariant prevents.

---

## CLI

```bash
aidbox-dqar ingest \
  --feed ehr-epic-447-clinical \
  --system epic-prod-org-447 \
  --pipeline interbox-job-20251014-ehr-001 \
  --measurement-period MY2026 \
  --bundle batch-2025-10-14.ndjson \
  --inputs hl7v2:epic-prod-org-447.oru-feed \
  --load-uc-props uc-properties.json     # optional; from client-kit
```

Exit non-zero if the `ConsistencyReport` contains any Tier 1 finding; print the
report regardless.

---

## End-to-End Test Shape

```python
def test_e2e_happy_path():
    report = orchestrator.run(...)        # well-formed batch + matching UC props
    assert report.consistent

def test_e2e_run_id_drift_is_tier1():
    # UC props carry a different ol_run_id than the emitted RunEvent
    report = orchestrator.run(...)
    assert any(f.linkage == 1 and f.severity == "tier_1" for f in report.findings)
```

---

## Phase 5 Success Criteria

- [ ] Orchestrator runs the canonical sequence: start → bundles → complete → load → validate
- [ ] One immutable `IngestContext` threads all four identifiers through the run
- [ ] Every AuditEvent gets EXT 6 (`ingest_pipeline_id`) and EXT 7 (`ol_run_id`)
- [ ] RunEvent `runId` == EXT 7 across the batch
- [ ] `fail_run()` called on any error; no unterminated START
- [ ] Resource + AuditEvent written as a single atomic transaction bundle
- [ ] `ConsistencyValidator` runs at the end; Tier 1 finding → non-zero exit
- [ ] RunEvents go to OpenMetadata; no Marquez dependency anywhere in the path
