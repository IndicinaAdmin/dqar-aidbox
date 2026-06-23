# Phase 1: UC Properties Loading (Weeks 1–2)

> **Boundary reminder:** This kit **loads** UC table properties that
> `cdar-client-kit` **generates**. It does not compute or re-derive property
> values. The source/feed/type/SSoR attribution that older designs placed in
> AuditEvent EXT 1–5 lives here, as Unity Catalog table properties. See
> `docs/UC_PROPERTIES_LOADING.md` for the full reference.

Apply the `uc-properties.json` (and/or `uc-properties.sql`) produced by client-kit
to a live Databricks Unity Catalog, via the SDK (automated) or Terraform
(change-controlled).

---

## Deliverables

1. **UCPropertiesLoader** (`aidbox_databricks/loaders/uc_properties_loader.py`)
   - Parse `uc-properties.json`
   - Validate every property key is `dqar_`-namespaced (reject otherwise)
   - Apply per table via `ALTER TABLE ... SET TBLPROPERTIES` (Databricks SDK)
   - Return an `applied / skipped / failed` result for reporting
2. **UCPropertiesLoadResult** (`aidbox_databricks/loaders/result.py`)
   - `applied: list[str]`, `skipped: list[str]`, `failed: list[tuple[str, str]]`
3. **Terraform module** (`terraform/databricks_uc_properties/`)
   - IaC path for CAB-reviewed application
4. **Tests** (`tests/test_uc_properties_loader.py`)
   - Namespace guard rejects non-`dqar_` keys
   - Missing tables land in `skipped`, not fatal
   - Idempotent re-apply (last-write-wins) overwrites cleanly

---

## Input Contract (from client-kit)

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

`dqar_lineage_ol_run_id` and `dqar_ingest_pipeline_id` are the **table-level echo**
of AuditEvent EXT 7 / EXT 6 — the most recent ingest that populated the table. The
per-resource truth lives in the AuditEvents (Phase 3); this is the per-table summary.

---

## Loader Sketch

```python
from __future__ import annotations
import json
from dataclasses import dataclass, field
from databricks.sdk import WorkspaceClient


@dataclass
class UCPropertiesLoadResult:
    applied: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)


class UCPropertiesLoader:
    """Applies client-kit-generated UC properties to Databricks. Load-only."""

    def __init__(self, workspace_url: str, token: str, catalog: str, warehouse_id: str):
        self._client = WorkspaceClient(host=workspace_url, token=token)
        self._catalog = catalog
        self._warehouse_id = warehouse_id

    def load_from_json(self, path: str) -> UCPropertiesLoadResult:
        doc = json.loads(open(path).read())
        result = UCPropertiesLoadResult()
        for table in doc["tables"]:
            fqn = f"{self._catalog}.{table['schema']}.{table['table_name']}"
            props = table["properties"]
            # Namespace guard — refuse anything not dqar_-prefixed
            bad = [k for k in props if not k.startswith("dqar_")]
            if bad:
                result.failed.append((fqn, f"non-dqar keys: {bad}"))
                continue
            try:
                if not self._table_exists(fqn):
                    result.skipped.append(fqn)
                    continue
                for key, value in props.items():
                    self._client.statement_execution.execute_statement(
                        warehouse_id=self._warehouse_id,
                        statement=f"ALTER TABLE {fqn} SET TBLPROPERTIES ('{key}' = '{value}')",
                    )
                result.applied.append(fqn)
            except Exception as e:  # report, don't abort the batch
                result.failed.append((fqn, str(e)))
        return result
```

Credentials are supplied by the caller (orchestrator / secret manager). The loader
never hardcodes a token, and never writes a non-`dqar_` key.

---

## Terraform Path (CAB-reviewed)

```hcl
variable "uc_properties_file" { type = string }
variable "databricks_host"    { type = string }
variable "databricks_token"   { type = string, sensitive = true }

provider "databricks" {
  host  = var.databricks_host
  token = var.databricks_token
}

locals {
  doc    = jsondecode(file(var.uc_properties_file))
  tables = { for t in local.doc.tables : "${t.schema}.${t.table_name}" => t }
}

resource "databricks_sql_table" "dqar_props" {
  for_each   = local.tables
  properties = each.value.properties
  # ... table identity ...
}
```

Use Terraform where property changes need CAB approval; use the SDK loader for
automated assessment pipelines.

---

## Idempotency

`ALTER TABLE ... SET TBLPROPERTIES` is last-write-wins per key. Re-running the
loader with a fresh assessment overwrites stale conformance/finding values cleanly
— safe to repeat, no duplicate accumulation. Each quarterly UC2 re-assessment
regenerates properties in client-kit; reload here to refresh.

---

## Consistency Check (the three-linkage invariant)

After loading, confirm the table property agrees with the lineage graph (Phase 2)
and AuditEvents (Phase 3):

```sql
SELECT
  tblproperties['dqar_source_feed_id']    AS feed,
  tblproperties['dqar_lineage_ol_run_id'] AS ol_run_id
FROM system.information_schema.tables
WHERE table_name = 'observation'
  AND tblproperties['dqar_organization_id'] = 'health-plan-123';
```

- `dqar_lineage_ol_run_id` must resolve to a RunEvent in OpenMetadata (Phase 2)
- `dqar_source_feed_id` must equal that RunEvent's `CDARIngestFacet.sourceFeedId`

Drift between the table property and the lineage facet is a **finding**, not just a
config error.

---

## Phase 1 Success Criteria

- [ ] Loader parses client-kit `uc-properties.json` and applies via SDK
- [ ] Namespace guard rejects any non-`dqar_` key (lands in `failed`)
- [ ] Missing tables reported in `skipped`, not fatal
- [ ] Re-apply is idempotent (last-write-wins)
- [ ] Terraform module applies the same properties for CAB-reviewed environments
- [ ] No property values computed here — load-only (generation is client-kit's job)

See the reference doc `docs/UC_PROPERTIES_LOADING.md` for SDK/Terraform/SQL detail.
