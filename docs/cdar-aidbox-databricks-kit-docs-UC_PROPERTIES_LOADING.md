# UC Properties Loading Reference

**cdar-aidbox-databricks-kit documentation**  
Version: June 2026  
Component: Databricks Unity Catalog load

---

## Generation vs. Loading — Know the Boundary

There are two halves to the UC properties story, owned by two different repos:

| Half | Owner | Doc |
|---|---|---|
| **Generate** the properties (from conformance results + manifest) | `cdar-client-kit` | client-kit `UC_PROPERTIES.md` |
| **Load** the properties into Databricks Unity Catalog | `cdar-aidbox-databricks-kit` (this kit) | this doc |

This kit does **not** define the property schema or compute the values — it consumes the `uc-properties.json` (and/or `uc-properties.sql`) that client-kit produces and applies them to the live Unity Catalog. For the full key reference (`dqar_source_system_id`, `dqar_source_feed_id`, `dqar_source_type`, `dqar_ecds_ssor_category`, the `dqar_conformance_level_*` keys, the `dqar_findings_tier_*` counts, and the lineage keys), see the client-kit `UC_PROPERTIES.md`. This doc covers only application.

> Recall the architecture: the source-attribution that older designs put in AuditEvent EXT 1–5 lives here, as UC table properties. The AuditEvent payload itself carries only EXT 6 + 7. See `AUDITEVENT_PROVENANCE.md`.

---

## Input: client-kit's `uc-properties.json`

The loader consumes the JSON form (the SQL form is for manual/CAB-reviewed application). Shape, abbreviated:

```json
{
  "organization_id": "health-plan-123",
  "measurement_period": "MY2026",
  "assessment_timestamp": "2025-10-14T22:30:00Z",
  "tables": [
    {
      "schema": "ehr_clinical",
      "table_name": "observation",
      "properties": {
        "dqar_organization_id": "health-plan-123",
        "dqar_source_system_id": "epic-prod-org-447",
        "dqar_source_feed_id": "ehr-epic-447-clinical",
        "dqar_source_type": "clinical_ehr",
        "dqar_ecds_ssor_category": "EHR/PHR",
        "dqar_conformance_level_3_pass_rate": "99.12",
        "dqar_findings_tier_2_count": "15",
        "dqar_lineage_ol_run_id": "a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
        "dqar_ingest_pipeline_id": "interbox-job-20251014-ehr-001"
      }
    }
  ]
}
```

Note `dqar_lineage_ol_run_id` and `dqar_ingest_pipeline_id` echo AuditEvent EXT 7/EXT 6 at the table level — the table-scoped record of the most recent ingest that populated it. The per-resource truth is in the AuditEvents; the per-table summary is here.

---

## Method 1 — Databricks SDK (programmatic)

```python
from dqar_aidbox_databricks_kit.loaders import UCPropertiesLoader

loader = UCPropertiesLoader(
    workspace_url="https://your-workspace.cloud.databricks.com",
    token=token,            # supplied by the caller; never hardcoded
    catalog="aidbox_catalog",
)

result = loader.load_from_json("uc-properties.json")
# result.applied: list of fully-qualified tables updated
# result.skipped: tables not found in UC (reported, not fatal)
# result.failed:  tables where ALTER failed (reported with error)
```

Internally each table is applied as:

```python
for table in doc["tables"]:
    fqn = f"{catalog}.{table['schema']}.{table['table_name']}"
    for key, value in table["properties"].items():
        client.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=f"ALTER TABLE {fqn} SET TBLPROPERTIES ('{key}' = '{value}')",
        )
```

> The loader validates that every property key is `dqar_`-namespaced before applying, so a malformed input can't write arbitrary table properties.

### Idempotency

`ALTER TABLE ... SET TBLPROPERTIES` is last-write-wins per key, so re-running the loader with a fresh assessment overwrites stale values cleanly. Loading is safe to repeat; it does not accumulate duplicate keys.

---

## Method 2 — Terraform (infrastructure-as-code)

For change-controlled environments, apply via Terraform so the property state is reviewable and versioned:

```hcl
variable "uc_properties_file" { type = string }
variable "databricks_host"    { type = string }
variable "databricks_token"   { type = string, sensitive = true }

provider "databricks" {
  host  = var.databricks_host
  token = var.databricks_token
}

locals {
  doc = jsondecode(file(var.uc_properties_file))
  tables = { for t in local.doc.tables : "${t.schema}.${t.table_name}" => t }
}

resource "databricks_sql_table" "dqar_props" {
  for_each = local.tables
  # ... table identity ...
  properties = each.value.properties
}
```

Apply:

```bash
terraform apply \
  -var="uc_properties_file=uc-properties.json" \
  -var="databricks_host=https://your-workspace.cloud.databricks.com" \
  -var="databricks_token=$DATABRICKS_TOKEN"
```

Use Terraform when a Change Advisory Board must review property changes before they hit production; use the SDK loader for automated assessment pipelines.

---

## Method 3 — SQL DDL (manual / CAB-reviewed)

client-kit also emits `uc-properties.sql` (one `ALTER TABLE ... SET TBLPROPERTIES` block per table, with comments). This is for manual application in the Databricks SQL editor or a reviewed migration. This kit does not transform it — apply it directly:

```bash
databricks sql --file uc-properties.sql
```

---

## Verification After Load

```sql
-- Confirm count of tables carrying CDAR properties for this assessment
SELECT COUNT(*) FROM system.information_schema.tables
WHERE tblproperties['dqar_organization_id'] = 'health-plan-123'
  AND tblproperties['dqar_measurement_period'] = 'MY2026';

-- Spot-check one table's source attribution + lineage linkage
SELECT
  tblproperties['dqar_source_feed_id']    AS feed,
  tblproperties['dqar_source_type']       AS source_type,
  tblproperties['dqar_lineage_ol_run_id'] AS ol_run_id
FROM system.information_schema.tables
WHERE table_name = 'observation'
  AND tblproperties['dqar_organization_id'] = 'health-plan-123';
```

Confirm the `dqar_lineage_ol_run_id` here matches a RunEvent resolvable in OpenMetadata (see `OPENMETADATA_INTEGRATION.md`) and the `dqar_source_feed_id` matches the `CDARIngestFacet.sourceFeedId` for the same dataset. Drift between the table property and the lineage facet is itself a finding.

---

## Loader Surface in This Kit

| Component | Responsibility |
|---|---|
| `UCPropertiesLoader` | Parse `uc-properties.json`, validate `dqar_`-namespacing, apply via SDK |
| `UCPropertiesLoadResult` | `applied` / `skipped` / `failed` breakdown for reporting |
| `terraform/databricks_uc_properties/` | IaC module for CAB-reviewed application |

---

## Best Practices

1. **Loading is the only job here.** Do not recompute or re-derive property values in this kit — if a value looks wrong, fix it in client-kit and regenerate. This kit applies; client-kit decides.
2. **Refresh on re-assessment.** Each quarterly UC2 re-assessment produces fresh properties; re-run the loader to overwrite stale conformance/finding values. Last-write-wins makes this safe.
3. **Keep table properties consistent with the lineage facet.** `dqar_source_feed_id`/`dqar_source_system_id` (UC) must equal `CDARIngestFacet.sourceFeedId`/`sourceSystemId` (OpenMetadata) for the same dataset.
4. **Prefer Terraform in production.** When property changes need approval, the IaC path gives a reviewable plan; the SDK loader is for automated pipelines.
5. **Never widen the namespace.** The loader rejects non-`dqar_` keys by design — keep it that way so a malformed input can't write arbitrary table metadata.
