# Usage Examples

> Scope: `dqar-aidbox-databricks-kit` — ingest-time operations. The CLI surface is
> `aidbox-dqar ingest`, not the `client-kit validate-*` commands (those are the
> assessment-time kit).

## Example 1: Full Ingest Run

```bash
aidbox-dqar ingest \
  --feed ehr-epic-447-clinical \
  --system epic-prod-org-447 \
  --pipeline interbox-job-20251014-ehr-001 \
  --measurement-period MY2026 \
  --bundle batch-2025-10-14.ndjson \
  --inputs hl7v2:epic-prod-org-447.oru-feed \
  --load-uc-props uc-properties.json
```

Sequence (see `05-phase-5-integration-orchestration.md`):
1. `start_run()` → `ol_run_id`
2. atomic resource + AuditEvent bundles (EXT 6 = pipeline, EXT 7 = `ol_run_id`)
3. `complete_run()` with `DQARIngestFacet`
4. load UC properties (if `--load-uc-props` given)
5. consistency validation → report

Exit is non-zero if any **Tier 1** consistency finding is present.

## Example 2: Load UC Properties Only (no ingest)

Apply a client-kit-generated properties document to Databricks via the SDK:

```bash
aidbox-dqar load-uc-props uc-properties.json \
  --catalog ehr_clinical \
  --warehouse-id 0123456789abcdef \
  --workspace-url https://your-workspace.cloud.databricks.com
# token from DATABRICKS_TOKEN env / secret manager — never on the command line
```

Result: `applied / skipped / failed` per table. Non-`dqar_` keys land in `failed`;
missing tables land in `skipped`.

## Example 3: Load UC Properties via Terraform (CAB-reviewed)

```bash
terraform init
terraform apply \
  -var="uc_properties_file=uc-properties.json" \
  -var="databricks_host=https://your-workspace.cloud.databricks.com"
# databricks_token supplied via TF_VAR_databricks_token (sensitive), not inline
```

## Example 4: The AuditEvent Written at Ingest (EXT 6 + 7 only)

Each resource is paired with this AuditEvent in a single atomic transaction bundle:

```json
{
  "resourceType": "Bundle",
  "type": "transaction",
  "entry": [
    {
      "fullUrl": "urn:uuid:obs-1",
      "request": { "method": "POST", "url": "Observation" },
      "resource": { "resourceType": "Observation", "id": "obs-1" }
    },
    {
      "request": { "method": "POST", "url": "AuditEvent" },
      "resource": {
        "resourceType": "AuditEvent",
        "entity": [{ "what": { "reference": "urn:uuid:obs-1" } }],
        "extension": [
          { "url": "https://sonian.io/fhir/ext/ingest-pipeline-id",
            "valueString": "interbox-job-20251014-ehr-001" },
          { "url": "https://sonian.io/fhir/ext/ol-run-id",
            "valueString": "a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d" }
        ]
      }
    }
  ]
}
```

Note: **only EXT 6 and EXT 7.** Source/feed/type/SSoR attribution lives in UC table
properties, not on the AuditEvent. The `urn:uuid:obs-1` placeholder is shared
between the resource `fullUrl` and the AuditEvent `entity.what.reference` so the
pair commits atomically.

## Example 5: The RunEvent Emitted to OpenMetadata

```json
{
  "eventType": "COMPLETE",
  "run": { "runId": "a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d" },
  "job": { "namespace": "interbox", "name": "ingest-ehr-epic-447-clinical" },
  "inputs": [{ "namespace": "hl7v2", "name": "epic-prod-org-447.oru-feed" }],
  "outputs": [{
    "namespace": "aidbox", "name": "Observation",
    "facets": {
      "dqarIngest": {
        "ingestPipelineId": "interbox-job-20251014-ehr-001",
        "sourceFeedId": "ehr-epic-447-clinical",
        "sourceSystemId": "epic-prod-org-447",
        "fieldMappings": [
          { "sourcePath": "OBX-5", "sourceSegment": "OBX",
            "targetPath": "Observation.valueQuantity.value",
            "translationTable": "loinc-units-v2.77", "translationTableVersion": "2.77" }
        ]
      }
    }
  }]
}
```

`runId` here equals AuditEvent EXT 7. To trace a resource: read its EXT 7 → look up
that `runId` in OpenMetadata → read inputs/outputs and `fieldMappings`. It is a
graph lookup, never a relational join.

## Example 6: Consistency Report (cross-kit)

```bash
aidbox-dqar validate-consistency \
  --uc-props uc-properties.json \
  --audit-events batch-auditevents.ndjson \
  --run-event run-a1b2c3d4.json
```

Output (illustrative):

```
Consistency: 1 finding
  [Tier 1] Linkage 1: AuditEvent EXT7 9f8e... != RunEvent.runId a1b2c3d4...
```

A clean run prints `Consistency: OK`. Tier 1 findings exit non-zero.

## Notes

- Provenance backend is **OpenMetadata**; there is no Marquez in this kit.
- Shared identifiers (`Engagement`, `MeasurementPeriod`, etc.) come from
  `dqar-contracts`; this kit does not define them.

See `docs/AUDITEVENT_PROVENANCE.md` for the authoritative EXT 6+7 reference and
`docs/OPENLINEAGE_EMISSION.md` for the full RunEvent lifecycle.
