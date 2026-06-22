# OpenMetadata Integration Reference

**dqar-aidbox-databricks-kit documentation**  
Version: June 2026  
Component: Catalog and lineage-graph layer

---

## Role of OpenMetadata in the Stack

OpenMetadata is the **catalog and lineage-graph layer**. It receives OpenLineage RunEvents from this kit and assembles the end-to-end lineage graph from each event's declared inputs and outputs. It is the single backend that answers "where did this dataset come from, and what fed it?"

The lineage stack principle:

- **OpenLineage** — the backbone protocol (the event format; see `OPENLINEAGE_EMISSION.md`)
- **OpenMetadata** — the catalog layer and the lineage backend that stores and serves the graph
- **Marquez** — the OpenLineage *reference* backend in the wider ecosystem, **dropped on the Indicina side**. RunEvents go directly to OpenMetadata.

The collapse from a four-tool stack (Aidbox-side Marquez + OpenMetadata + ...) to three tools is intentional: one fewer deployed service, one fewer place for the graph to live, and no `lineage_resource_map` join table (that table existed only as a join key to Marquez and has been dropped entirely).

---

## How the Graph Is Assembled

OpenMetadata builds lineage from the **declared inputs and outputs** of each RunEvent — not from any per-resource foreign key.

```
RunEvent (runId R1)
  inputs:  [ hl7v2:epic-prod-org-447.oru-feed ]
  outputs: [ aidbox:Observation ]  + DQARIngestFacet(fieldMappings)
       │
       ▼
OpenMetadata edge:  hl7v2:epic-prod-org-447.oru-feed ──▶ aidbox:Observation
       with field-level mappings (OBX-5 → Observation.valueQuantity.value, ...)
```

Each RunEvent contributes one or more edges. Over many runs, OpenMetadata accumulates the full source→FHIR graph, including field-level edges from the `DQARIngestFacet`.

### The `ol-run-id` is a lookup key, not a join key

AuditEvent EXT 7 (`ol-run-id`) tags each resource with the `runId` that produced it. To trace a resource:

1. Read the resource's AuditEvent EXT 7 → get `runId`.
2. Look up that `runId` in OpenMetadata → get the RunEvent's declared inputs/outputs and `fieldMappings`.
3. The graph (already assembled by OpenMetadata) tells you the upstream sources and the field-level transformations.

You never SQL-join resources to a lineage table on the UUID. There is no such table. The UUID resolves a run; the run's declared I/O (held in OpenMetadata) holds the relationships.

---

## What Lives in OpenMetadata

| Artifact | Source | Purpose |
|---|---|---|
| Dataset entities | RunEvent inputs/outputs | Nodes in the lineage graph (source feeds, FHIR datasets) |
| Lineage edges | RunEvent input→output declarations | The graph itself |
| Field-level lineage | `DQARIngestFacet.fieldMappings` | Source-field → FHIR-field edges with translation-table versions |
| Run history | RunEvent START/COMPLETE/FAIL | Audit trail of ingest runs by `runId` |

---

## Querying Lineage

OpenMetadata exposes the graph through its lineage API. Typical DQAR queries:

**Trace a resource to its source:**
```
1. resource → AuditEvent EXT 7 → runId
2. GET /api/v1/lineage/openlineage/run/{runId}   → inputs, outputs, fieldMappings
3. Read upstream dataset(s) and the field mappings that produced each FHIR field
```

**Find every FHIR dataset fed by a given source feed:**
```
GET /api/v1/lineage/{datasetFqn}?upstreamDepth=0&downstreamDepth=3
  where datasetFqn = hl7v2:epic-prod-org-447.oru-feed
→ all downstream FHIR datasets and the runs that produced them
```

**Confirm provenance-maturity coverage (Level 3+):**
```
For a sample of resources:
  - read AuditEvent EXT 7 (ol-run-id)
  - confirm each runId resolves to a RunEvent in OpenMetadata
  - confirm the RunEvent carries a DQARIngestFacet with fieldMappings
Coverage % of resolvable runIds with field mappings = the maturity signal.
```

---

## Boundary with Databricks Unity Catalog

OpenMetadata and Databricks UC hold **complementary** metadata; do not conflate them:

| Question | Answered by |
|---|---|
| "Where did this dataset come from? What transformed it field-by-field?" | **OpenMetadata** (lineage graph from RunEvents) |
| "What feed/system/type/SSoR does this *table* represent, and how conformant is it?" | **Databricks UC table properties** (see `UC_PROPERTIES_LOADING.md`) |
| "Which ingest run produced this *exact resource*?" | **AuditEvent EXT 6 + 7** (see `AUDITEVENT_PROVENANCE.md`) |

The `DQARIngestFacet` deliberately mirrors `sourceFeedId`/`sourceSystemId` into the lineage graph so the graph is self-describing — but the authoritative per-table attribution lives in UC properties, and the two must stay consistent (drift is a finding).

---

## What This Kit Does NOT Do with OpenMetadata

- ❌ Does not deploy or depend on Marquez
- ❌ Does not maintain a `lineage_resource_map` join table (dropped)
- ❌ Does not assemble the graph itself — OpenMetadata does, from declared I/O
- ❌ Does not store source attribution only in the graph — UC properties are the authoritative catalog copy

---

## Best Practices

1. **Treat OpenMetadata as the single lineage backend.** If a design reintroduces Marquez as a second store, the graph can diverge — emit to one backend.
2. **Declare complete inputs and outputs on every RunEvent.** The graph is only as good as the declarations; a COMPLETE event missing its output dataset leaves an orphaned run.
3. **Resolve, don't join.** When building DQAR risk-stratification queries, resolve `ol-run-id` → RunEvent → graph. Do not attempt a relational join on the UUID.
4. **Keep facet and UC properties in lockstep.** A nightly check that `DQARIngestFacet.sourceFeedId` matches the dataset's `dqar_source_feed_id` UC property catches drift early.
5. **Verify run closure.** Periodically query for STARTed runs with no COMPLETE/FAIL — these indicate aborted ingests and undermine provenance-maturity coverage.
