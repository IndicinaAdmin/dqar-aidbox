# OpenLineage Emission Reference

**dqar-aidbox-databricks-kit documentation**  
Version: June 2026  
Component: Lineage event emission

---

## What This Kit Emits

For every ingest batch, the orchestrator emits **OpenLineage RunEvents** describing the run's inputs, outputs, and field-level transformations. These RunEvents go **directly to OpenMetadata** — Marquez has been dropped as a deployed service on the Indicina side. OpenMetadata builds the lineage graph from each RunEvent's declared inputs and outputs.

The `runId` of the RunEvent is the value written into AuditEvent **EXT 7 (`ol-run-id`)** for every resource produced in that batch (see `AUDITEVENT_PROVENANCE.md`). That is the linkage between a FHIR resource and its lineage run — but the graph itself is assembled in OpenMetadata, not by joining on `ol-run-id`.

```
Interbox ingest batch
   │  produces FHIR resources (each tagged with ol-run-id in AuditEvent EXT 7)
   │
   ├─ emits START RunEvent  ─┐
   ├─ emits COMPLETE RunEvent ┘ → OpenMetadata (lineage graph assembled here)
   │       carries DQARIngestFacet (field mappings)
   ▼
OpenMetadata catalog: inputs → outputs graph + field-level lineage
```

---

## RunEvent Lifecycle

Each ingest batch emits at least two RunEvents sharing one `runId`:

| Event type | When | Carries |
|---|---|---|
| `START` | batch begins | run identity, job reference, inputs (source datasets) |
| `COMPLETE` | batch succeeds | outputs (FHIR datasets), `DQARIngestFacet` with field mappings |
| `FAIL` | batch errors | error facet; emit instead of COMPLETE on failure |

```json
{
  "eventType": "COMPLETE",
  "eventTime": "2025-10-14T21:45:00.000Z",
  "run": {
    "runId": "a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d"
  },
  "job": {
    "namespace": "interbox",
    "name": "ingest-ehr-epic-447-clinical"
  },
  "inputs": [
    {
      "namespace": "hl7v2",
      "name": "epic-prod-org-447.oru-feed",
      "facets": {}
    }
  ],
  "outputs": [
    {
      "namespace": "aidbox",
      "name": "Observation",
      "facets": {
        "dqarIngest": { "...DQARIngestFacet (see below)..." }
      }
    }
  ],
  "producer": "https://sonian.io/dqar-aidbox-databricks-kit/1.0.0",
  "schemaURL": "https://openlineage.io/spec/2-0-2/OpenLineage.json#/definitions/RunEvent"
}
```

The `runId` here (`a1b2c3d4-...`) is exactly what lands in AuditEvent EXT 7 for every resource this batch wrote.

---

## The DQARIngestFacet

The custom `DQARIngestFacet` is attached to each **output dataset** in the COMPLETE RunEvent. It captures the field-level mapping from the source message structure to FHIR fields — the heart of what makes Study Type 2 (EHR Clinical Data Feed Completeness) mechanically executable rather than a manual field-by-field trace.

```json
{
  "dqarIngest": {
    "_producer": "https://sonian.io/dqar-aidbox-databricks-kit/1.0.0",
    "_schemaURL": "https://sonian.io/dqar/facets/DQARIngestFacet.json",
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
| `ingestPipelineId` | Mirrors AuditEvent EXT 6 — the job that ran |
| `sourceFeedId` / `sourceSystemId` | Mirror the UC-property source attribution for this output dataset (the facet is the lineage-graph copy; the table properties are the catalog copy) |
| `fieldMappings[]` | Per-field source→FHIR transformation, with the translation table and its version |
| `fieldMappings[].sourceSegment` | The HL7v2 segment (e.g., `OBX`) the field came from |
| `fieldMappings[].translationTableVersion` | Version of the mapping table applied — the audit anchor for "which mapping produced this value?" |

### Why field mappings matter

The `fieldMappings` array is the "mappings as code" pattern made observable: each message transformation emits a typed, versioned field-level mapping into the lineage graph. With it, a Study Type 2 analyst answers "where did `Observation.valueQuantity.value` come from, and under which translation table version?" as a graph query — not a multi-day manual reconstruction from ETL docs.

Level 3 maturity (the MP2029 floor) requires: versioned mapping code, OpenLineage event emission carrying the `fieldMappings` facet, and the RunEvent stored in the lineage backend (OpenMetadata).

---

## Direct Emission to OpenMetadata

RunEvents are POSTed to OpenMetadata's OpenLineage-compatible ingestion endpoint. There is no intermediate Marquez instance on the Indicina side.

```python
from dqar_aidbox_databricks_kit.lineage import OpenLineageEmitter

emitter = OpenLineageEmitter(
    endpoint="https://openmetadata.example.com/api/v1/lineage/openlineage",
    api_token=token,  # supplied by orchestrator, never hardcoded
    producer="https://sonian.io/dqar-aidbox-databricks-kit/1.0.0",
)

run_id = emitter.start_run(
    job_namespace="interbox",
    job_name="ingest-ehr-epic-447-clinical",
    inputs=[{"namespace": "hl7v2", "name": "epic-prod-org-447.oru-feed"}],
)
# ... orchestrator threads run_id into IngestContext so AuditEvent EXT 7 matches ...

emitter.complete_run(
    run_id=run_id,
    outputs=[{
        "namespace": "aidbox",
        "name": "Observation",
        "dqar_ingest_facet": dqar_ingest_facet,  # the DQARIngestFacet dict
    }],
)
```

> The `OpenLineageEmitter` never holds credentials directly — the orchestrator passes a short-lived token. On failure, emit a `FAIL` RunEvent with the same `runId` so the lineage graph records the aborted run rather than leaving a dangling START.

---

## Linkage to AuditEvent EXT 7

The contract between this doc and `AUDITEVENT_PROVENANCE.md`:

1. Orchestrator calls `start_run()` → receives `run_id`.
2. Orchestrator stores `run_id` in `IngestContext`.
3. Every AuditEvent written during the batch sets EXT 7 (`ol-run-id`) = `run_id`.
4. Orchestrator calls `complete_run()` with the `DQARIngestFacet`.
5. OpenMetadata assembles the input→output graph and field-level lineage from the RunEvent.

To trace a resource's origin: read its AuditEvent EXT 7, look up that `runId` in OpenMetadata, and read the RunEvent's declared inputs/outputs and `fieldMappings`. You never SQL-join resources to lineage on the UUID — the UUID is the lookup key into the graph, and the graph holds the relationships.

---

## Best Practices

1. **One `runId` per ingest batch**, shared by START/COMPLETE/FAIL and by every AuditEvent EXT 7 in the batch. Generate it once at `start_run()`.
2. **Always close the run.** Emit COMPLETE on success or FAIL on error — a START with no terminal event leaves the graph inconsistent and fails provenance-maturity checks.
3. **Version every translation table** in `fieldMappings`. An unversioned mapping is unauditable; "which mapping produced this value" must resolve to a specific version.
4. **Keep the facet and the UC properties consistent.** `sourceFeedId`/`sourceSystemId` in the facet must match the `dqar_source_feed_id`/`dqar_source_system_id` UC table properties for the same output dataset. They are two views of one truth; drift between them is itself a finding.
5. **Emit to OpenMetadata, not Marquez.** Marquez may appear in older specs as the reference backend — on the Indicina side it is dropped; emit directly to OpenMetadata.
