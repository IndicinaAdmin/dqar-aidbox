# cdar-aidbox-databricks-kit Quickstart

**cdar-aidbox-databricks-kit documentation**  
Version: June 2026

---

## What This Kit Does

It is the bridge between Aidbox (FHIR) and Databricks (analytics), with lineage to OpenMetadata. Three jobs:

1. **Write provenance** — pair each ingested resource with a two-extension AuditEvent (EXT 6 + 7) in atomic transaction bundles
2. **Emit lineage** — send OpenLineage RunEvents (with the `CDARIngestFacet` field mappings) to OpenMetadata
3. **Load UC properties** — apply client-kit's generated UC table properties to Databricks Unity Catalog

It consumes what `cdar-client-kit` produces; it does not generate UC properties or run conformance checks itself.

---

## Install

```bash
pip install cdar-aidbox-databricks-kit>=1.0.0,<2.0.0
```

Optional extras:

```bash
pip install "cdar-aidbox-databricks-kit[databricks]"   # Databricks SDK loader
pip install "cdar-aidbox-databricks-kit[openlineage]"  # OpenLineage client
```

Verify:

```bash
cdar-aidbox-databricks-kit --version
cdar-aidbox-databricks-kit --help
```

---

## Prerequisites

| Need | For |
|---|---|
| Aidbox configured per `AIDBOX_SETUP.md` | Writing resource + AuditEvent bundles |
| OpenMetadata endpoint + token | Emitting RunEvents |
| Databricks workspace + warehouse + token | Loading UC properties |
| `uc-properties.json` from client-kit | The properties to load |

---

## 15-Minute Walkthrough

### Step 1 — Configure connections

Set connection details via environment (tokens come from your secret store, never hardcoded):

```bash
export AIDBOX_BASE_URL="https://aidbox.example.com"
export AIDBOX_CLIENT_ID="dqar-ingest-client"
export OPENMETADATA_URL="https://openmetadata.example.com"
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
# tokens/secrets supplied at runtime by your secret manager
```

### Step 2 — Start a lineage run

```python
from dqar_aidbox_databricks_kit.lineage import OpenLineageEmitter

emitter = OpenLineageEmitter(endpoint=OPENMETADATA_URL + "/api/v1/lineage/openlineage",
                             api_token=token,
                             producer="https://sonian.io/cdar-aidbox-databricks-kit/1.0.0")

run_id = emitter.start_run(
    job_namespace="interbox",
    job_name="ingest-ehr-epic-447-clinical",
    inputs=[{"namespace": "hl7v2", "name": "epic-prod-org-447.oru-feed"}],
)
```

### Step 3 — Write resources with provenance

```python
from dqar_aidbox_databricks_kit.provenance import IngestContext, TransactionBundleAssembler

ctx = IngestContext(
    ingest_pipeline_id="interbox-job-20251014-ehr-001",
    ol_run_id=run_id,   # ← same UUID as the lineage run; lands in AuditEvent EXT 7
)

assembler = TransactionBundleAssembler(ctx)

bundle = assembler.pair(resource={
    "resourceType": "Observation",
    "status": "final",
    "code": {"coding": [{"system": "http://loinc.org", "code": "4548-4"}]},
    "subject": {"reference": "Patient/p1"},
    "valueQuantity": {"value": 7.2, "unit": "%"},
})

# POST the transaction bundle to Aidbox (resource + AuditEvent, atomic)
assembler.post(bundle, aidbox_url=AIDBOX_BASE_URL, token=aidbox_token)
```

### Step 4 — Complete the lineage run with field mappings

```python
emitter.complete_run(
    run_id=run_id,
    outputs=[{
        "namespace": "aidbox",
        "name": "Observation",
        "dqar_ingest_facet": {
            "ingestPipelineId": "interbox-job-20251014-ehr-001",
            "sourceFeedId": "ehr-epic-447-clinical",
            "sourceSystemId": "epic-prod-org-447",
            "fieldMappings": [
                {"sourcePath": "OBX-5", "sourceSegment": "OBX",
                 "targetPath": "Observation.valueQuantity.value",
                 "translationTable": "loinc-units-v2.77", "translationTableVersion": "2.77"},
            ],
        },
    }],
)
```

### Step 5 — Load UC properties from client-kit

```python
from dqar_aidbox_databricks_kit.loaders import UCPropertiesLoader

loader = UCPropertiesLoader(workspace_url=DATABRICKS_HOST, token=db_token, catalog="aidbox_catalog")
result = loader.load_from_json("uc-properties.json")
print(f"Applied: {len(result.applied)}  Skipped: {len(result.skipped)}  Failed: {len(result.failed)}")
```

### Step 6 — Verify the three linkages

```sql
-- UC property carries the lineage run id (table-level echo of EXT 7)
SELECT tblproperties['dqar_lineage_ol_run_id']
FROM system.information_schema.tables
WHERE table_name = 'observation';
```

```
- AuditEvent EXT 7 on each resource == run_id from Step 2
- That run_id resolves to a RunEvent in OpenMetadata (Step 4)
- The RunEvent's CDARIngestFacet.sourceFeedId == the table's dqar_source_feed_id
```

If all three line up, provenance is intact end to end.

---

## Where to Go Next

- **Provenance contract details** → `AUDITEVENT_PROVENANCE.md`
- **Lineage events & field mappings** → `OPENLINEAGE_EMISSION.md`
- **Graph assembly & querying** → `OPENMETADATA_INTEGRATION.md`
- **Loading mechanics (SDK / Terraform / SQL)** → `UC_PROPERTIES_LOADING.md`
- **Aidbox configuration** → `AIDBOX_SETUP.md`
- **When something breaks** → `TROUBLESHOOTING.md`
