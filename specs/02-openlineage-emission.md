# Phase 2: OpenLineage Event Emission (Weeks 3–4)

> **Architecture lock:** RunEvents are emitted **directly to OpenMetadata** —
> Marquez is dropped on the Indicina side. The RunEvent `runId` is the value
> written into AuditEvent **EXT 7 (`ol-run-id`)** for every resource in the batch
> (Phase 3). `ol-run-id` is an ingest batch tag and graph **lookup key**, not a
> relational join key — OpenMetadata assembles the graph from declared inputs and
> outputs. See `docs/OPENLINEAGE_EMISSION.md`.

Emit OpenLineage RunEvents from each ingest batch, carrying the `CDARIngestFacet`
with field-level mappings, to OpenMetadata.

---

## Deliverables

1. **OpenLineageEmitter** (`aidbox_databricks/lineage/openlineage_emitter.py`)
   - `start_run()` → returns `run_id` (UUID)
   - `complete_run()` with outputs + `CDARIngestFacet`
   - `fail_run()` on error (same `run_id`)
2. **CDARIngestFacet builder** (`aidbox_databricks/lineage/dqar_ingest_facet.py`)
   - `ingestPipelineId`, `sourceFeedId`, `sourceSystemId`
   - `fieldMappings[]` with `sourcePath`, `sourceSegment`, `targetPath`, `translationTable`, `translationTableVersion`
3. **OpenMetadata client** (`aidbox_databricks/clients/openmetadata_client.py`)
   - POST RunEvents to the OpenLineage-compatible ingestion endpoint
   - Retry/backoff; token supplied by caller, never hardcoded
4. **Tests** (`tests/test_openlineage_emission.py`)
   - START/COMPLETE share one `run_id`
   - COMPLETE carries `CDARIngestFacet` with versioned `fieldMappings`
   - FAIL emitted on error path; no dangling START

---

## RunEvent Lifecycle

| Event | When | Carries |
|---|---|---|
| `START` | batch begins | run identity, job ref, input datasets (source feeds) |
| `COMPLETE` | batch succeeds | output datasets (FHIR) + `CDARIngestFacet` |
| `FAIL` | batch errors | error facet (instead of COMPLETE) |

```json
{
  "eventType": "COMPLETE",
  "eventTime": "2025-10-14T21:45:00.000Z",
  "run": { "runId": "a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d" },
  "job": { "namespace": "interbox", "name": "ingest-ehr-epic-447-clinical" },
  "inputs": [{ "namespace": "hl7v2", "name": "epic-prod-org-447.oru-feed" }],
  "outputs": [{
    "namespace": "aidbox",
    "name": "Observation",
    "facets": { "dqarIngest": { "...CDARIngestFacet..." } }
  }],
  "producer": "https://sonian.io/cdar-aidbox-databricks-kit/1.0.0",
  "schemaURL": "https://openlineage.io/spec/2-0-2/OpenLineage.json#/definitions/RunEvent"
}
```

The `runId` here is exactly what lands in AuditEvent EXT 7 for the batch.

---

## CDARIngestFacet

Attached to each output dataset in the COMPLETE event. The `fieldMappings` array is
the "mappings as code" pattern made observable — it makes Study Type 2 (EHR
Clinical Data Feed Completeness) a graph query instead of a manual trace.

```json
{
  "dqarIngest": {
    "_producer": "https://sonian.io/cdar-aidbox-databricks-kit/1.0.0",
    "_schemaURL": "https://sonian.io/dqar/facets/CDARIngestFacet.json",
    "ingestPipelineId": "interbox-job-20251014-ehr-001",
    "sourceFeedId": "ehr-epic-447-clinical",
    "sourceSystemId": "epic-prod-org-447",
    "fieldMappings": [
      {
        "sourcePath": "OBX-5",
        "sourceSegment": "OBX",
        "targetPath": "Observation.valueQuantity.value",
        "translationTable": "loinc-units-v2.77",
        "translationTableVersion": "2.77"
      },
      {
        "sourcePath": "OBX-3",
        "sourceSegment": "OBX",
        "targetPath": "Observation.code.coding",
        "translationTable": "local-to-loinc-map",
        "translationTableVersion": "2025.09"
      }
    ]
  }
}
```

| Field | Purpose |
|---|---|
| `ingestPipelineId` | Mirrors AuditEvent EXT 6 |
| `sourceFeedId` / `sourceSystemId` | Mirror the UC-property source attribution for this dataset |
| `fieldMappings[].sourceSegment` | HL7v2 segment (e.g., `OBX`) the field came from |
| `fieldMappings[].translationTableVersion` | The audit anchor for "which mapping produced this value" |

**Level 3 maturity (MP2029 floor)** requires versioned mapping code + this
`fieldMappings` facet + the RunEvent stored in OpenMetadata. An unversioned mapping
fails the maturity check.

---

## Emitter Sketch

```python
from __future__ import annotations
import uuid


class OpenLineageEmitter:
    def __init__(self, endpoint: str, api_token: str, producer: str):
        self._endpoint = endpoint
        self._token = api_token            # supplied by caller; never hardcoded
        self._producer = producer

    def start_run(self, job_namespace: str, job_name: str, inputs: list[dict]) -> str:
        run_id = str(uuid.uuid4())
        self._emit("START", run_id, job_namespace, job_name, inputs=inputs, outputs=[])
        return run_id

    def complete_run(self, run_id: str, job_namespace: str, job_name: str,
                     outputs: list[dict]) -> None:
        # each output may carry a CDARIngestFacet under outputs[i]["facets"]["dqarIngest"]
        self._emit("COMPLETE", run_id, job_namespace, job_name, inputs=[], outputs=outputs)

    def fail_run(self, run_id: str, job_namespace: str, job_name: str, error: str) -> None:
        self._emit("FAIL", run_id, job_namespace, job_name, inputs=[], outputs=[], error=error)
```

> Always close a run: emit COMPLETE on success or FAIL on error. A START with no
> terminal event leaves the graph inconsistent and fails provenance-maturity checks.

---

## Linkage to Phase 3 (AuditEvent EXT 7)

The contract between this phase and Phase 3:

1. Orchestrator calls `start_run()` → receives `run_id`.
2. Orchestrator stores `run_id` in `IngestContext` (Phase 3).
3. Every AuditEvent in the batch sets EXT 7 (`ol-run-id`) = `run_id`.
4. Orchestrator calls `complete_run()` with the `CDARIngestFacet`.
5. OpenMetadata assembles the input→output + field-level graph.

To trace a resource: read its AuditEvent EXT 7 → look up that `runId` in
OpenMetadata → read declared I/O and `fieldMappings`. Never a relational join on the
UUID.

---

## Phase 2 Success Criteria

- [ ] START / COMPLETE share one `run_id` per ingest batch
- [ ] COMPLETE declares both inputs and outputs (no orphaned runs)
- [ ] `CDARIngestFacet` present with versioned `fieldMappings`
- [ ] FAIL emitted on error; no dangling START
- [ ] RunEvents POST to **OpenMetadata** (not Marquez)
- [ ] `run_id` is threaded to Phase 3 so AuditEvent EXT 7 matches
- [ ] `CDARIngestFacet.sourceFeedId` matches the dataset's UC `dqar_source_feed_id` (consistency)

See the reference doc `docs/OPENLINEAGE_EMISSION.md` for the full RunEvent lifecycle.
