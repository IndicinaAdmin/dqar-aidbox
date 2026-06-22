# Acceptance Criteria

> Scope: `dqar-aidbox-databricks-kit`. These criteria gate the ingest-time kit:
> UC property loading, OpenLineage emission, AuditEvent provenance, cross-kit
> consistency, and orchestration. (Conformance / manifest / 5-level criteria
> belong to `dqar-client-kit`, not here.)

## Build & Package
- [ ] `pyproject.toml` valid and installable
- [ ] `pip install .` succeeds and resolves `dqar-contracts>=1.0.0,<2.0.0`
- [ ] `aidbox-dqar --version` works
- [ ] `aidbox-dqar ingest --help` shows the ingest options
- [ ] Shared types imported from `dqar_contracts.shared` (no local redefinition)

## Phase 1 — UC Properties Loading
- [ ] Parses client-kit `uc-properties.json`
- [ ] Namespace guard rejects any non-`dqar_` key (lands in `failed`)
- [ ] Missing tables reported in `skipped`, not fatal
- [ ] Re-apply is idempotent (last-write-wins)
- [ ] Terraform module applies the same properties for CAB-reviewed environments
- [ ] **No property values computed** — load-only

## Phase 2 — OpenLineage Emission
- [ ] START / COMPLETE share one `run_id` per batch
- [ ] COMPLETE declares both inputs and outputs (no orphaned runs)
- [ ] `DQARIngestFacet` present with **versioned** `fieldMappings` (sourceSegment, targetPath, translationTableVersion)
- [ ] FAIL emitted on error; no dangling START
- [ ] RunEvents POST to **OpenMetadata** (Marquez absent from the dependency tree and the code path)

## Phase 3 — AuditEvent Provenance
- [ ] AuditEvent carries **only EXT 6 (`ingest-pipeline-id`) and EXT 7 (`ol-run-id`)**
- [ ] Builder **rejects** any source-attribution extension (no EXT 1–5 on the AuditEvent)
- [ ] **No source-inference code path exists** anywhere in the kit
- [ ] Resource + AuditEvent written as a single atomic FHIR transaction bundle (`type: "transaction"`, shared `urn:uuid:` placeholder)

## Phase 4 — Integration with client-kit
- [ ] `ConsistencyValidator` checks all three identity linkages
- [ ] Linkage 1 (run identity: EXT 7 == RunEvent.runId == UC `dqar_lineage_ol_run_id`) mismatch → Tier 1 finding
- [ ] Linkage 2 (feed: UC `dqar_source_feed_id` == `DQARIngestFacet.sourceFeedId`) mismatch → Tier 2 finding
- [ ] Linkage 3 (resource missing EXT 7) → Tier 2 finding
- [ ] Validator returns findings; does not raise

## Phase 5 — Orchestration
- [ ] Canonical sequence: start → atomic bundles → complete → load → validate
- [ ] One immutable `IngestContext` threads all four identifiers through the run
- [ ] RunEvent `runId` == EXT 7 across the batch
- [ ] `fail_run()` on any error; no unterminated START
- [ ] Tier 1 consistency finding → non-zero CLI exit; report printed regardless

## Testing
- [ ] Unit coverage of loaders/, lineage/, orchestration/
- [ ] OpenMetadata + Aidbox HTTP mocked (no live services in CI)
- [ ] End-to-end happy path + at least one consistency-failure path
- [ ] All tests pass on Python 3.10, 3.11, 3.12
- [ ] CI/CD runs on every push

## Documentation
- [ ] `docs/UC_PROPERTIES_LOADING.md`, `docs/OPENLINEAGE_EMISSION.md`, `docs/AUDITEVENT_PROVENANCE.md` present and consistent with specs
- [ ] `docs/AUDITEVENT_PROVENANCE.md` is the authoritative EXT 6+7 reference
- [ ] README quickstart for the ingest path
- [ ] `docs/TROUBLESHOOTING.md` for OpenMetadata/Databricks/Aidbox auth issues

## Deployment
- [ ] Package publishable internally
- [ ] Credentials sourced from secret manager — never hardcoded
- [ ] Installation tested on Linux, macOS
