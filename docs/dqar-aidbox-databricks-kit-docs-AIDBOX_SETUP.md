# Aidbox Setup Reference

**dqar-aidbox-databricks-kit documentation**  
Version: June 2026  
Component: Aidbox configuration for the kit

---

## What This Kit Needs from Aidbox

This kit writes resource + AuditEvent pairs into Aidbox via transaction bundles and relies on a few Aidbox capabilities being configured. This doc covers the minimum Aidbox setup; it is not a full Aidbox guide (see Health Samurai docs for that).

Required:
- FHIR Schema validation enabled
- US Core 6.1.0 loaded (the conformance target)
- The two AuditEvent extension definitions registered
- An AccessPolicy permitting the kit's client to write transaction bundles
- Configuration committed as an Init Bundle (infrastructure-as-code)

---

## The Atomicity Guarantee (why bundles matter)

Aidbox's transaction atomicity applies **only within a single bundle POST**. The kit pairs every resource with its AuditEvent in one `type: "transaction"` bundle precisely because of this — split across two POSTs and a partial failure leaves a resource without provenance (or an AuditEvent pointing at a resource that was never written). See `AUDITEVENT_PROVENANCE.md` for the bundle shape.

Aidbox defaults to **SERIALIZABLE** isolation, which prevents serialization anomalies but can reject transactions under high concurrency. For high-volume ingest, weigh relaxing per-request isolation via the `x-max-isolation-level` header — but do so deliberately for clinical data, and never at the cost of the resource↔AuditEvent atomicity (that pairing must stay in one bundle regardless of isolation level).

---

## Enabling FHIR Schema Validation

The current validation engine is FHIR Schema (the Zen-lang validator is deprecated). Enable it:

```bash
BOX_FEATURES_FHIR_SCHEMA_VALIDATION=true
```

Load US Core 6.1.0 as the conformance target (USCDI v3; the version required under CMS-0057-F):

```bash
AIDBOX_FHIR_PACKAGES=hl7.fhir.us.core#6.1.0
```

Or via the FHIR Package API:

```
POST /fhir/ImplementationGuide/$load
{ "id": "hl7.fhir.us.core", "version": "6.1.0" }
```

---

## Registering the Two AuditEvent Extensions

The kit writes exactly two extensions on the AuditEvent (EXT 6 + 7). Register their definitions so they validate. As FHIR Schema definitions:

```json
{
  "resourceType": "FHIRSchema",
  "id": "dqar-ingest-pipeline-id",
  "url": "http://sonian.io/fhir/ext/ingest-pipeline-id",
  "type": "Extension",
  "base": "Extension",
  "elements": {
    "url": { "type": "uri", "fixed": "http://sonian.io/fhir/ext/ingest-pipeline-id" },
    "valueString": { "type": "string", "required": true }
  }
}
```

```json
{
  "resourceType": "FHIRSchema",
  "id": "dqar-ol-run-id",
  "url": "http://sonian.io/fhir/ext/ol-run-id",
  "type": "Extension",
  "base": "Extension",
  "elements": {
    "url": { "type": "uri", "fixed": "http://sonian.io/fhir/ext/ol-run-id" },
    "valueString": { "type": "string", "required": true }
  }
}
```

> Do not register source-type / source-system-id / source-feed-id / inference-confidence / ecds-ssor extensions. Those are **not** AuditEvent extensions in this architecture — that attribution lives in Unity Catalog table properties (see `UC_PROPERTIES_LOADING.md`). Registering them here would invite the stale seven-extension pattern back in.

---

## AccessPolicy for the Ingest Client

The kit authenticates as a dedicated client and needs permission to POST transaction bundles. Use client-credentials with a scoped Matcho policy (avoid the allow-all policy outside local dev):

```json
{
  "resourceType": "Client",
  "id": "dqar-ingest-client",
  "secret": "set-via-secret-file-not-here",
  "grant_types": ["client_credentials"]
}
```

```json
{
  "resourceType": "AccessPolicy",
  "id": "dqar-ingest-write",
  "engine": "matcho",
  "matcho": {
    "client": { "id": "dqar-ingest-client" },
    "request-method": "post",
    "uri": { "$one-of": ["#/$", "#/fhir/$"] }
  }
}
```

> The client secret must be supplied via a mounted secret file, never an env var or a committed Init Bundle. Treat credential entry as out of scope for automation — configure the secret out of band.

---

## Init Bundle (infrastructure-as-code)

Commit the Aidbox configuration — IG packages, the two extension definitions, the Client, and the AccessPolicy — as an Init Bundle loaded at startup, so the whole configuration lives in git:

```bash
AIDBOX_INIT_BUNDLE_PATH=/config/dqar-init-bundle.json
```

Init Bundle skeleton:

```json
{
  "resourceType": "Bundle",
  "type": "transaction",
  "entry": [
    { "request": {"method": "PUT", "url": "FHIRSchema/dqar-ingest-pipeline-id"}, "resource": { "...EXT 6 schema..." } },
    { "request": {"method": "PUT", "url": "FHIRSchema/dqar-ol-run-id"},          "resource": { "...EXT 7 schema..." } },
    { "request": {"method": "PUT", "url": "Client/dqar-ingest-client"},           "resource": { "...client (secret via file)..." } },
    { "request": {"method": "PUT", "url": "AccessPolicy/dqar-ingest-write"},       "resource": { "...policy..." } }
  ]
}
```

---

## macOS Gatekeeper Note (local dev)

When running Aidbox tooling or the Claude Code native binary locally on macOS, the binary may be quarantined by Gatekeeper. Clear the quarantine attribute:

```bash
xattr -d com.apple.quarantine /path/to/binary
```

---

## Verification

```bash
# FHIR Schema validation on
curl -s "$AIDBOX/$version" | grep -i fhir-schema   # or check settings UI

# Extensions registered
curl -s "$AIDBOX/fhir/StructureDefinition?url=http://sonian.io/fhir/ext/ol-run-id"

# Client can write a transaction bundle (smoke test with a throwaway resource)
# → POST a minimal Observation + AuditEvent transaction bundle, expect 200
```

---

## Best Practices

1. **Configuration as code.** Keep IG packages, extension definitions, client, and policy in the Init Bundle under git — no hand-configured production Aidbox.
2. **Two extensions, registered and no more.** Registering only EXT 6 + 7 makes the validator itself enforce the lean AuditEvent contract.
3. **Scoped AccessPolicy, secret out of band.** Never put the client secret in the Init Bundle or env vars; mount it as a secret file.
4. **Preserve in-bundle atomicity under any isolation setting.** If you relax `x-max-isolation-level` for throughput, the resource + AuditEvent must still be one bundle.
5. **Avoid deprecated patterns.** No Zen-lang validator, no AidboxProfile resources, no Entity/Attribute model — FHIR Schema + StructureDefinition only.
