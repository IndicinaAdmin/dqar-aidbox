# dqar-aidbox-databricks-kit Troubleshooting

**dqar-aidbox-databricks-kit documentation**  
Version: June 2026

---

## Provenance / AuditEvent Issues

### Resource written but no AuditEvent (or vice versa)

**Cause:** the resource and AuditEvent were not in the same transaction bundle, or a `batch` bundle was used instead of `transaction`.

**Fix:**
- Confirm `bundle.type == "transaction"` (not `"batch"` — batch entries succeed/fail independently).
- Confirm both entries are in one bundle and the AuditEvent's `entity.what.reference` uses the same `urn:uuid:` placeholder as the resource's `fullUrl`.
- Re-POST the pair as a single transaction bundle. See `AUDITEVENT_PROVENANCE.md`.

### AuditEvent rejected: unknown extension

**Cause:** the EXT 6 / EXT 7 extension definitions are not registered in Aidbox, or an attempt was made to write a source-type/source-system extension (which is not part of this architecture).

**Fix:**
- Register the two extension FHIRSchemas (`AIDBOX_SETUP.md`).
- If the rejected extension is `source-type`, `source-system-id`, `source-feed-id`, `source-inference-confidence`, or `ecds-ssor` — remove it. Those belong in UC table properties, not the AuditEvent.

### Transaction rejected under load (serialization failure)

**Cause:** Aidbox's default SERIALIZABLE isolation rejecting concurrent transactions.

**Fix:**
- Retry with backoff (serialization failures are transient).
- For sustained high-volume ingest, consider `x-max-isolation-level` per request — but keep the resource + AuditEvent in one bundle regardless. Weigh carefully for clinical data.

---

## OpenLineage Emission Issues

### `ol-run-id` in AuditEvent resolves to nothing in OpenMetadata

**Cause:** the AuditEvent was written with a `run_id` but the RunEvent was never emitted (or only a START was emitted, never COMPLETE/FAIL).

**Fix:**
- Ensure the orchestrator calls `complete_run()` (or `fail_run()`) for every `start_run()`.
- Confirm the same `run_id` from `start_run()` is threaded into `IngestContext.ol_run_id` so EXT 7 matches the emitted RunEvent.
- Query OpenMetadata for STARTed-but-not-closed runs and close or re-emit them.

### RunEvent emitted but no edge appears in the graph

**Cause:** the COMPLETE event declared no outputs (or no inputs), so OpenMetadata has nothing to connect.

**Fix:**
- Confirm `complete_run()` includes both the input dataset(s) and the output dataset(s).
- A run with an empty `outputs` array produces no lineage edge — populate it.

### `DQARIngestFacet` missing field mappings

**Cause:** the facet was attached without `fieldMappings`, or mappings lack `translationTableVersion`.

**Fix:**
- Populate `fieldMappings[]` with `sourcePath`, `sourceSegment`, `targetPath`, and a versioned `translationTable`.
- An unversioned mapping is unauditable and fails provenance-maturity Level 3+. Add the version.

---

## OpenMetadata Issues

### Emission returns 401 / 403

**Cause:** missing or expired OpenMetadata API token.

**Fix:**
- The `OpenLineageEmitter` takes a token from the caller — confirm the orchestrator supplies a current one. Rotate if expired. Never hardcode it in the kit.

### Lineage looks incomplete / stops at a boundary

**Cause:** runs upstream of Aidbox (e.g., dbt transformations) are not emitting OpenLineage events — a pre-FHIR lineage gap.

**Fix:**
- This is expected if the upstream layer is uninstrumented; it surfaces as a Tier 3 finding in client-kit's dbt detection.
- It is not a bug in this kit. This kit instruments the ingest→FHIR hop; upstream instrumentation is a separate remediation (see client-kit `DBT_INTEGRATION.md`).

### Reintroduced Marquez causes divergent graphs

**Cause:** RunEvents being emitted to both Marquez and OpenMetadata.

**Fix:**
- Emit to OpenMetadata only. Marquez is dropped on the Indicina side. Two backends = two graphs that drift.

---

## UC Properties Loading Issues

### `Table not found` during load

**Cause:** a table in `uc-properties.json` doesn't exist in the target catalog/schema.

**Fix:**
- These appear in `result.skipped`, not as fatal errors — review the list.
- Confirm the `catalog` passed to `UCPropertiesLoader` matches where the tables actually live, and that the schema/table names in the JSON match Databricks.

### Loader rejects a property key

**Cause:** a non-`dqar_`-namespaced key in the input. The loader rejects these by design.

**Fix:**
- This indicates a malformed `uc-properties.json`. Regenerate it from client-kit; do not hand-edit keys. The namespace guard is intentional — it prevents writing arbitrary table metadata.

### Properties applied but values look stale

**Cause:** an old assessment's `uc-properties.json` was loaded, or the loader ran before a fresh client-kit assessment.

**Fix:**
- Re-run the client-kit assessment, then re-run the loader with the fresh JSON. `SET TBLPROPERTIES` is last-write-wins, so the new values overwrite cleanly.

### `dqar_source_feed_id` (UC) ≠ `DQARIngestFacet.sourceFeedId` (OpenMetadata)

**Cause:** the table property and the lineage facet drifted — different feed attribution for the same dataset.

**Fix:**
- This is a genuine finding, not just a config error. Determine which is correct (the manifest is the source of truth), regenerate the side that's wrong, and reload/re-emit. Add a nightly consistency check to catch it early.

---

## Databricks Connection Issues

### SDK auth failure

**Fix:**
```bash
databricks auth profiles          # confirm a working profile
databricks workspace ls /         # smoke-test connectivity
```
Confirm the warehouse ID used for statement execution is running and the token has UC modify rights.

---

## Repo Rename Issues (post Step 0)

### `import dqar_aidbox` fails after rename

**Cause:** the package import was changed when only the repo/folder should have been renamed (default scope keeps the package name `dqar_aidbox`).

**Fix:**
- Under the default scope, the importable package stays `dqar_aidbox`; only the repo folder becomes `dqar-aidbox-databricks-kit`. Revert any import-path rewrites unless an explicit package rename was requested.

### Stray `dqar-aidbox` references remain

**Fix:**
```bash
grep -rIn --exclude-dir=.git 'dqar-aidbox\b' .   # the \b excludes the new suffixed name
```
Update or justify each remaining hit; references in sibling repos are handled by their own rename steps, not this one.

---

## Getting Help

- **GitHub Issues:** https://github.com/Indicina/dqar-aidbox-databricks-kit/issues
- **Aidbox / Health Samurai:** https://connect.health-samurai.io/ (Zulip)
- Enable verbose logging: `dqar-aidbox --verbose <command>`
