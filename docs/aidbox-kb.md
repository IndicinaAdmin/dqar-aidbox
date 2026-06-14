# Aidbox Knowledge Base
> Comprehensive architectural and implementation reference for Claude Code.
> Source: https://www.health-samurai.io/docs/aidbox — last fetched June 2026.

---

## Table of Contents
1. [Platform overview](#1-platform-overview)
2. [Architecture fundamentals](#2-architecture-fundamentals)
3. [Database & storage](#3-database--storage)
4. [FHIR vs Aidbox formats](#4-fhir-vs-aidbox-formats)
5. [Querying strategies](#5-querying-strategies)
6. [API surface](#6-api-surface)
7. [FHIR search](#7-fhir-search)
8. [Bulk & batch APIs](#8-bulk--batch-apis)
9. [GraphQL & subscriptions](#9-graphql--subscriptions)
10. [Authentication & identity](#10-authentication--identity)
11. [Access policies & authorization](#11-access-policies--authorization)
12. [SMART on FHIR](#12-smart-on-fhir)
13. [Terminology module](#13-terminology-module)
14. [Profiling & validation](#14-profiling--validation)
15. [Subscriptions & event streaming](#15-subscriptions--event-streaming)
16. [Integration toolkit](#16-integration-toolkit)
17. [SQL on FHIR](#17-sql-on-fhir)
18. [AI & MCP tools](#18-ai--mcp-tools)
19. [SDKs & developer tooling](#19-sdks--developer-tooling)
20. [Deployment & operations](#20-deployment--operations)
21. [Observability](#21-observability)
22. [Multitenancy](#22-multitenancy)
23. [Decision guide](#23-decision-guide)
24. [Deprecated patterns to avoid](#24-deprecated-patterns-to-avoid)

---

## 1. Platform Overview

Aidbox is a **backend development platform** for healthcare applications — not just a FHIR server. It provides reusable infrastructure for EHRs, patient-facing apps, analytics platforms, and integration engines.

### Core capabilities

| Capability | Detail |
|---|---|
| FHIR-native storage | PostgreSQL + JSONB; every resource type gets two tables (current + history) |
| Multi-API | FHIR REST, SQL, GraphQL, Bulk, Subscriptions, Changes API, RPC |
| FHIR versions | STU3, R4, R4B, R5, R6 (preview) — multiple versions can coexist |
| Artifact registry | 500+ IGs: US Core, Da Vinci, mCode, IPS, national (US, DE, CA…) |
| Terminology | Built-in ICD-10, SNOMED CT, LOINC, RxNorm, NPI, CVX, CPT |
| Security | OAuth 2.0, SMART on FHIR, RBAC/ABAC, access policies, FHIR BALP audit |
| Integration | HL7 v2, C-CDA, X12, Apple HealthKit, email, analytics (Tableau, Power BI) |
| AI / MCP | Built-in MCP server (v2505+) exposing FHIR CRUD to LLM agents via SSE |

### Compliance & certifications

- HIPAA compliant
- ISO 27001:2022 certified
- HL7 International member
- ONC Health IT certification capable ((g)(7), (g)(9), (g)(10))
- CMS-0057-F capable (CRD, PAS)

### Deployment options

| Option | Best for |
|---|---|
| `curl -JO https://aidbox.app/runme && docker compose up` | Local dev, prototyping |
| Aidbox Sandbox (cloud) | Evaluation, demos |
| AWS Marketplace | Production on AWS |
| Kubernetes (Helm charts) | Production at scale |
| Managed PostgreSQL (RDS, Cloud SQL, Azure DB) | Teams with existing DB ops |

---

## 2. Architecture Fundamentals

### Metadata-driven design

Everything in Aidbox is a **resource** — including meta-resources like REST endpoints (OperationDefinitions), resource definitions (StructureDefinitions), profiles, and access policies. Meta-resources follow the same REST rules as clinical resources. This means:

- Adding a new resource type or profile automatically generates DB schema, REST endpoints, and validation rules
- System configuration is done through the same FHIR API as data operations
- No server restarts required for most configuration changes

### Dual API architecture

| Base path | Format | Use |
|---|---|---|
| `/fhir/*` | FHIR format | External consumers, SMART apps, interop — always use this for anything outside your control |
| `/*` | Aidbox native format | Internal services where you own both sides; avoids format conversion overhead |

On-the-fly conversion happens at the `/fhir` layer. The internal format is isomorphic to FHIR but differs in how `id`, `meta`, and some extensions are stored.

### Request processing pipeline

```
Incoming HTTP request
  → Authentication (token / Basic / JWT)
  → Access policy evaluation
  → Operation routing (FHIR or Aidbox endpoint)
  → Resource validation (FHIR Schema)
  → PostgreSQL read/write (JSONB)
  → Response + audit log (AuditEvent)
```

### Extensibility patterns

| Pattern | Mechanism | When to use |
|---|---|---|
| First-class extensions | StructureDefinition with extension slicing | Standard FHIR extension approach |
| Custom resources | StructureDefinition with custom resourceType | Domain entities outside FHIR spec |
| Custom operations | OperationDefinition + Aidbox App | Custom business logic endpoints |
| Aidbox Apps | External microservice registered as plugin | Complex workflows, any language/runtime |
| Mappings | Integration toolkit mapping rules | Data transformation pipelines |

---

## 3. Database & Storage

Aidbox uses **PostgreSQL + JSONB** as its single source of truth. No separate search indexes, no dual writes, no ETL to a secondary store.

### Two-table pattern

For every resource type (e.g. `Patient`), Aidbox creates exactly two tables:

| Table | Purpose |
|---|---|
| `patient` | Current version only. Fast reads. Used for all active queries and searches. |
| `patient_history` | Every version ever written. Soft deletes leave a deletion marker here. |

### Row structure

| Column | Type | Purpose |
|---|---|---|
| `id` | text | Resource identifier (UUID or client-provided) |
| `txid` | bigint | Global transaction sequence — enables cross-resource change ordering |
| `ts` | timestamptz | Last updated (`meta.lastUpdated`) |
| `cts` | timestamptz | Created timestamp |
| `status` | text | `created` / `updated` / `deleted` |
| `resource` | jsonb | Full FHIR resource body (minus id/meta — stored as columns) |

**Why separate columns for id/meta?** Avoids storing them redundantly in JSONB while enabling fast `WHERE id = ?` queries without JSON parsing.

### Direct SQL access

```sql
-- Basic extraction
SELECT id, resource->>'gender', resource->'name'->0->>'family'
FROM patient
WHERE resource->>'active' = 'true';

-- Containment search (fast with GIN index)
SELECT * FROM patient
WHERE resource @> '{"identifier":[{"system":"ssn","value":"123-45"}]}';

-- JSONPath
SELECT * FROM observation
WHERE jsonb_path_query_first(resource, '$.subject.reference') = 'Patient/abc';

-- Nested extraction
SELECT id, resource#>>'{name,0,given,0}' as first_name FROM patient;

-- Parameterized via /$sql endpoint
POST /$sql
["SELECT count(*) FROM patient WHERE resource->>'gender' = ?", "female"]
```

### CRUD mechanics

**Create** — inserts into main table with status `created` and `txid` from global sequence.

**Update** — two-step atomic operation:
1. Copy current row to `patient_history`
2. Update main table with new resource, new `txid`, status `updated`

**Delete (soft)** — three-step:
1. Copy current row to `patient_history`
2. Insert a deletion marker row in `patient_history` with status `deleted`
3. Remove from main table

After deletion: resource invisible in searches, but full history preserved in `patient_history` for HIPAA compliance.

### Point-in-time queries

```sql
-- What did the resource look like on a specific date?
SELECT * FROM patient_history
WHERE id = 'patient-123'
  AND ts <= '2024-01-01'::timestamptz
ORDER BY txid DESC
LIMIT 1;

-- All changes in last hour
SELECT id, txid, ts, status FROM patient_history
WHERE ts > CURRENT_TIMESTAMP - INTERVAL '1 hour'
ORDER BY txid DESC;
```

### Transaction isolation

Aidbox defaults to **SERIALIZABLE isolation**. This prevents all serialization anomalies but can cause transaction rejections under high concurrency. Relax per-request with the `x-max-isolation-level` header — weigh carefully for clinical data.

### PostgreSQL requirements

- **Minimum:** PostgreSQL 12 (requires JSONB path support)
- **Recommended:** PostgreSQL 15–18
- **Managed services:** AWS RDS, Google Cloud SQL, Azure Database for PostgreSQL all supported
- **Extensions:** `pg_trgm`, `pgcrypto`, `uuid-ossp`, optional `postgis`

### Read-only replica pattern

Aidbox can delegate read queries to a PostgreSQL replica, isolating heavy search/analytics loads from the write primary. Critical for high-traffic deployments where slow searches could starve writes.

```
[aidbox app] → writes → [primary postgres]
[aidbox app] → reads  → [replica postgres]
```

---

## 4. FHIR vs Aidbox Formats

### Key differences

| Aspect | FHIR format (`/fhir/*`) | Aidbox format (`/*`) |
|---|---|---|
| `id` field | Inside resource JSON | Stored as separate DB column |
| `meta` fields | Inside `meta` object | Stored as DB columns (`ts`, `txid`) |
| Extensions | Array of `extension` objects | First-class fields in some custom types |
| Conversion cost | On-the-fly at /fhir layer | None |
| Use for interop | ✅ Required | ❌ Internal only |

**Rule:** Always use `/fhir/*` for any consumer outside your direct control (third-party apps, SMART apps, partner integrations, any external system).

### First-class extensions

Aidbox lets you define extensions as top-level fields on custom resource types via StructureDefinition. Extension data becomes a direct JSONB field — far more queryable than nested extension arrays.

```json
// Standard FHIR extension (nested, harder to query)
{ "extension": [{"url": "race", "valueCode": "2054-5"}] }

// Aidbox first-class extension (direct field, easy to query)
{ "race": {"code": "2054-5", "system": "urn:oid:2.16.840.1.113883.6.238"} }
```

Use `$to-format` endpoint to convert between formats explicitly when needed.

---

## 5. Querying Strategies

Three approaches, each optimized for different workloads:

| Approach | Best for | Consumer |
|---|---|---|
| **FHIR Search** | Clinical workflows, SMART apps, external consumers | Any FHIR client |
| **Direct SQL** | Complex analytics, custom joins, max flexibility | Internal services, BI tools |
| **SQL on FHIR** | BI/analytics with flat tabular views | Tableau, Power BI, dbt, data teams |

### FHIR search → SQL translation

| Search type | Example | PostgreSQL operator |
|---|---|---|
| Token | `?gender=male` | JSONB containment `@>` |
| Reference | `?subject=Patient/123` | `jsonb_path_query_first` |
| String | `?name=Smith` | `ILIKE` on extracted text |
| Date | `?birthdate=gt1990-01-01` | Cast and compare timestamptz |
| Number/Quantity | `?value-quantity=5.4` | Numeric extract + comparison |
| Composite | `?component-code-value-quantity` | Correlated sub-expressions |

### Index strategy

- **GIN indexes** — default for JSONB containment (`@>`). Auto-created for registered SearchParameters.
- **Expression indexes** — for frequently-queried extracted paths. Create manually for custom SQL query patterns.

After large data loads, review and rebuild indexes via the Indexes module.

---

## 6. API Surface

### All APIs at a glance

| API | Base path | Best for |
|---|---|---|
| FHIR REST | `/fhir` | Interop, SMART apps, external consumers |
| Aidbox REST | `/` | Internal services, performance-critical paths |
| GraphQL | `/$graphql` | Frontend apps, flexible projections, reduce over-fetching |
| SQL endpoint | `/$sql` | Analytics, complex queries, parameterized SQL over HTTP |
| Bulk export | `/$export`, `/$dump`, `/$dump-sql`, `/$dump-csv` | Large-scale data export |
| Bulk import | `/$import`, `/$load` | Large-scale data import |
| Batch/Transaction | `/` (Bundle) | Multi-resource atomic operations |
| Changes API | `/[type]/$changes` | ETL feeds, event-driven sync, cursor-based polling |
| Subscriptions | FHIR topic-based | Real-time push notifications |
| RPC API | `/rpc` | Custom business operations |
| Archive/Restore | `/[type]/$archive` | Cold storage for old resources |
| Encryption | `/$encrypt` | Field-level encryption at rest |
| Sequence | `/$sequence` | Ordered ID generation |
| Batch Upsert | `PUT /[type]` | Lightweight collection replace |
| Cache | Header-based | Response caching with invalidation |
| ETag | `If-Match` header | Conditional requests, prevent lost updates |
| `$everything` | `/Patient/[id]/$everything` | Full patient compartment in one call |
| `$validate` | `/[type]/$validate` | Validate without writing |
| Capability Statement | `/fhir/metadata` | CapabilityStatement / conformance |

### Bundle types

| Type | Behavior | Use |
|---|---|---|
| Transaction | All-or-nothing; internal references resolved before execution | Create linked resources atomically (Patient + Encounter + Observation) |
| Batch | Each entry independent; partial success possible | Bulk data ops where individual failures are acceptable |

**Internal reference resolution in transactions:** Use `urn:uuid:temp-id` as `fullUrl` for new resources within the bundle. Aidbox resolves these to real IDs before execution — no need to pre-generate IDs.

```json
{
  "resourceType": "Bundle",
  "type": "transaction",
  "entry": [
    {
      "fullUrl": "urn:uuid:patient-temp",
      "request": {"method": "POST", "url": "Patient"},
      "resource": {"resourceType": "Patient", "name": [{"family": "Smith"}]}
    },
    {
      "request": {"method": "POST", "url": "Observation"},
      "resource": {
        "resourceType": "Observation",
        "subject": {"reference": "urn:uuid:patient-temp"}
      }
    }
  ]
}
```

---

## 7. FHIR Search

### Search parameter types

| Type | Example | Notes |
|---|---|---|
| token | `?gender=male`, `?identifier=ssn\|123` | Coded values, identifiers, booleans |
| string | `?name=Smith` | Partial, case-insensitive |
| reference | `?subject=Patient/123` | Resource references |
| date | `?birthdate=gt1990-01-01` | Supports `eq`, `ne`, `lt`, `gt`, `le`, `ge`, `sa`, `eb`, `ap` |
| quantity | `?value-quantity=5.4\|\|mg` | Numeric + unit |
| uri | `?url=http://...` | Canonical URIs |
| composite | `?component-code-value-quantity` | Multi-field combinations |
| special | `?_text=fever`, `?_content` | Full-text search |

### Modifiers

```
?name:exact=Smith        # Case-sensitive exact match
?name:contains=mith      # Substring anywhere
?subject:Patient.name=S  # Chained search
?_has:Observation:subject:code=1234-5  # Reverse chain
```

### Common parameters

| Parameter | Purpose |
|---|---|
| `_include` | Include referenced resources in response |
| `_revinclude` | Include resources that reference the result |
| `_elements` | Project specific fields (reduce payload) |
| `_count` | Page size |
| `_page` | Page number (or use `_offset`) |
| `_sort` | Sort order (prefix `-` for descending) |
| `_total` | Control total count computation (`none`, `estimate`, `accurate`) |
| `_summary` | Return summary representation |

### Custom SearchParameters

Register via Artifact Registry → Aidbox auto-creates DB index → immediately available, no restart required.

```json
{
  "resourceType": "SearchParameter",
  "id": "patient-race",
  "url": "http://example.com/fhir/SearchParameter/patient-race",
  "name": "race",
  "status": "active",
  "description": "Patient race extension",
  "code": "race",
  "base": ["Patient"],
  "type": "token",
  "expression": "Patient.extension.where(url='http://hl7.org/fhir/us/core/StructureDefinition/us-core-race').extension.value"
}
```

> **Performance note:** Custom SearchParameters traversing nested arrays may need manual expression indexes. Always test with production-scale data before go-live.

### Aidbox Search extensions

- `_ilike` — case-insensitive substring across text fields
- Aidbox Search resource — define reusable named queries with pre-compiled SQL

---

## 8. Bulk & Batch APIs

### Import operations

| Operation | Endpoint | Notes |
|---|---|---|
| `$import` | `POST /$import` | FHIR Bulk Data spec-compliant. NDJSON from URLs (S3, GCS, Azure). Async with status polling. |
| `$load` | `POST /[type]/$load` | Aidbox-native, faster. Direct NDJSON stream. Skips some validation for speed. |
| `$fhir/import` | `POST /fhir/$import` | FHIR-spec import at `/fhir` path |
| Batch upsert | `PUT /[type]` | Lightweight in-memory collection replace; good for reference data |
| Bulk import from S3 | config-based | Stream directly from S3 bucket |

### Export operations

| Operation | Endpoint | Output |
|---|---|---|
| `$export` | `GET /$export` | FHIR Bulk Data spec; async; NDJSON to S3/GCS/Azure |
| `$dump` | `GET /[type]/$dump` | Streaming NDJSON; no file storage needed |
| `$dump-sql` | `POST /$dump-sql` | CSV/NDJSON from arbitrary SQL select |
| `$dump-csv` | `GET /[type]/$dump-csv` | CSV export of a resource type |
| `$purge` | `DELETE /[type]/$purge` | Bulk delete by criteria |

### Migration pattern

```
Initial load from external FHIR source  → $import
Repeat loads where you control format   → $load (faster)
Normal transactional multi-resource ops → Transaction Bundle
High-speed migration (direct DB access) → PostgreSQL COPY
```

### PostgreSQL COPY (maximum throughput)

For initial migrations, direct COPY bypasses HTTP overhead entirely:

```sql
COPY patient (id, txid, status, resource) FROM STDIN WITH (FORMAT csv);
patient-1,100001,created,"{""name"":[{""family"":""Johnson""}]}"
patient-2,100002,created,"{""name"":[{""family"":""Williams""}]}"
\.
```

---

## 9. GraphQL & Subscriptions

### GraphQL API

Endpoint: `POST /$graphql`

Schema auto-generated from loaded StructureDefinitions. Supports queries, filtering, and included references.

```graphql
query {
  PatientList(name: "Smith", _count: 10) {
    id
    name { family given }
    gender
    birthDate
    ObservationList(_reference: subject) {
      code { coding { code display } }
      valueQuantity { value unit }
    }
  }
}
```

### Topic-based subscriptions

Aidbox implements FHIR R5 topic-based subscriptions (also backported to R4/R4B).

**Model:**
```
SubscriptionTopic (defines trigger criteria)
  → Subscription (channel + optional filter)
    → Notification bundle (delivered to endpoint)
```

**Channel types:**

| Channel | Protocol | Best for |
|---|---|---|
| `rest-hook` | HTTP POST | Webhooks, microservice event handling |
| `websocket` | WebSocket | Real-time UI updates, low-latency dashboards |
| `email` | SMTP | Notification emails for clinical events |
| `message` | FHIR messaging | Interop with FHIR messaging-based systems |

**AidboxTopicDestination extensions** (beyond standard FHIR channels):

- Kafka topic
- ClickHouse
- GCP Pub/Sub
- AWS EventBridge
- AWS SNS
- NATS
- RabbitMQ
- ActiveMQ
- BigQuery
- Webhook (enhanced)

### Changes API (polling alternative)

```
GET /Patient/$changes?_since=txid&_count=100
```

Cursor-based, reliable, no persistent connection needed. Returns all changes since a given `txid`. Ideal for ETL, sync pipelines, and systems where polling is preferable to push.

**Subscriptions vs Changes API decision:**

| Use subscriptions when | Use Changes API when |
|---|---|
| You need push (not pull) | Consumer controls the polling rate |
| Sub-second latency matters | Guaranteed delivery via cursor is critical |
| Stable receiving endpoint exists | ETL/sync pipelines where batching is fine |
| FHIR interop consumers involved | Simpler infra (no webhook endpoint needed) |

### AidboxTrigger

A server-side trigger module (distinct from subscriptions) that executes custom logic in response to resource lifecycle events within Aidbox itself — useful for enforcing invariants or cascading updates without an external listener.

---

## 10. Authentication & Identity

### Identity providers

| Provider | Notes |
|---|---|
| Built-in Aidbox IDP | Manages Users, Clients, Sessions natively. Good for smaller deployments. |
| External OIDC | Okta, Azure AD, Keycloak, Google, GitHub, Apple, any OIDC-compliant provider |
| SSO | Configure via `IdentityProvider` resource; auto-create users from foreign tokens |

### OAuth 2.0 flows

| Flow | Use case |
|---|---|
| Authorization Code | Web apps with user login |
| Client Credentials | Machine-to-machine, backend services |
| Resource Owner Password | Legacy integrations (avoid where possible) |
| Implicit | Legacy SPA apps (deprecated in OAuth 2.1) |
| Token Exchange | Delegation, impersonation scenarios |
| Token Introspection | Validate opaque tokens from external issuers |

### Authentication methods

| Method | Use case |
|---|---|
| Basic Auth | Simple internal service auth, dev/testing |
| Bearer JWT | Stateless token auth from any OIDC provider |
| OAuth 2.0 tokens | User-delegated access from web/mobile apps |
| SMART on FHIR | EHR-integrated app launch with contextual scopes |
| mTLS (client certs) | High-trust backend service communication |
| Two-Factor Auth | Built-in 2FA support for user accounts |

### SSO with Okta/Azure AD/Keycloak

Configure an `IdentityProvider` resource pointing to the external IdP's discovery endpoint. Aidbox will use OIDC for auth and can auto-create `User` resources from successful logins via the token hook pattern.

---

## 11. Access Policies & Authorization

### Policy evaluation model

- AccessPolicy resources are evaluated for every request
- A request is **allowed if any matching policy returns `true`**
- Policies match on request properties: method, URL, user attributes, JWT claims, resource content
- Two engines: **Matcho DSL** (declarative pattern matching) or **SQL** (arbitrary query)

### Authorization mechanisms

| Mechanism | How it works | Best for |
|---|---|---|
| AccessPolicy (ABAC) | Matcho DSL rules match on any request/user attribute | Fine-grained attribute-based control |
| RBAC | Roles assigned to users; policies reference roles | Standard role-based permission models |
| SMART scopes | Restrict by FHIR resource type and operation | Third-party SMART app authorization |
| Label-based AC | Security labels on resources; policies filter by label | Sensitivity-based data classification |
| Scoped API | Patient/Organization/Compartment context enforced at API level | Patient portal, multi-org tenancy |
| Hierarchical AC | Access to parent implies access to children | Org hierarchy, care team scoping |
| Consent-based AC | FHIR Consent resources drive access decisions | Patient-controlled data sharing |

### Matcho DSL example

```json
{
  "resourceType": "AccessPolicy",
  "id": "nurses-read-patients",
  "engine": "matcho",
  "matcho": {
    "uri": "#/fhir/Patient/.*",
    "request-method": {"$enum": ["get", "head"]},
    "user": {
      "role": "nurse",
      "organization": {"$present": true}
    }
  }
}
```

### RBAC pattern

```json
{
  "resourceType": "AccessPolicy",
  "id": "admin-full-access",
  "engine": "matcho",
  "matcho": {
    "user": {"roles": {"$contains": {"role": {"id": "admin"}}}}
  }
}
```

### Label-based access control

Tag sensitive resources with security labels. Policies can then filter based on label values — useful for VIP patient records, sensitive diagnoses, etc.

### Audit logging

- **FHIR BALP:** Creates `AuditEvent` resources for every API operation — who, what, when, result. Query at `GET /fhir/AuditEvent`.
- **OpenTelemetry:** Structured logs and traces exportable to Loki, Datadog, CloudWatch, Elastic, etc.
- **Custom log extensions:** Add application-specific fields to Aidbox log events.

### Best practices

- Keep policies specific — narrow policies matching few request patterns are easier to reason about than broad policies with complex exclusions
- Debug with `GET /$debug/access-control` before deploying
- Use the `AccessPolicy` dev tool (Aidbox UI) for interactive testing
- Prefer ABAC for fine-grained control; use RBAC for coarser role-based gates

---

## 12. SMART on FHIR

Aidbox implements SMART on FHIR v1 and v2.

### Launch contexts

| Context | Description |
|---|---|
| EHR launch | App launched from within an EHR. Launch context includes patient, encounter, and user. Requires EHR to pass launch token. |
| Standalone launch | App launched independently. User selects patient context during authorization. Common for patient-facing apps. |

### Scope patterns

| Scope | Meaning |
|---|---|
| `patient/Patient.r` | Read the current patient's Patient resource |
| `patient/Observation.rs` | Read + search Observations for current patient |
| `user/Observation.crud` | Full CRUD on Observations in current user's context |
| `system/Patient.read` | System-level read of all Patients |
| `launch/patient` | Request patient context during launch |
| `openid fhirUser` | OIDC identity + FHIR user resource |

### Authentication methods for SMART clients

| Method | Use case |
|---|---|
| Symmetric (client secret) | Confidential apps with a stored secret |
| Asymmetric (private key JWT) | Apps that can securely hold a private key; more secure |

### ONC Inferno compliance

Aidbox passes ONC Inferno test suites for SMART App Launch. The (g)(10) certification path is documented in Solutions → ONC Health IT Certification Program.

**Smartbox:** Health Samurai's dedicated SMART on FHIR authorization server — a pre-configured Aidbox deployment optimized for (g)(10) compliance.

---

## 13. Terminology Module

### Built-in terminologies

ICD-10-CM, SNOMED CT, LOINC, RxNorm, US NPI, CVX (vaccines), CPT

### FHIR terminology operations

| Operation | Endpoint | Purpose |
|---|---|---|
| `$validate-code` | `GET /fhir/CodeSystem/$validate-code` | Check if a code is valid in a system |
| `$expand` | `GET /fhir/ValueSet/$expand` | Get all codes in a value set |
| `$lookup` | `GET /fhir/CodeSystem/$lookup` | Get display name and properties for a code |
| `$translate` | `GET /fhir/ConceptMap/$translate` | Map a code from one system to another |
| `$subsumes` | `GET /fhir/CodeSystem/$subsumes` | Hierarchy check (is A a subtype of B?) |

### Hybrid mode

Aidbox Terminology Module can run in hybrid mode — use Aidbox's built-in terminology for some operations and delegate to an external FHIR terminology server (e.g., Ontoserver, Snowstorm) for others.

### Custom terminologies

Load custom CodeSystem and ValueSet resources via the Artifact Registry. They participate in all standard terminology operations immediately — no server config needed.

### Performance notes

- SNOMED CT is large (~350k concepts) — consider pre-warming `$expand` results for large hierarchies on startup
- ValueSet expansion is cached; pre-compute large hierarchical expansions explicitly
- For high-frequency code validation on every resource write, consider async validation mode or batching

---

## 14. Profiling & Validation

### FHIR Schema validator

Current validation engine is **FHIR Schema** — replaced the deprecated Zen-lang validator. Validates against FHIR StructureDefinitions using a modern, performant approach.

Enable it:
```
BOX_FEATURES_FHIR_SCHEMA_VALIDATION=true
```

### Artifact registry — where profiles live

| Artifact type | Purpose |
|---|---|
| StructureDefinition | Resource profiles, custom resources, extensions |
| SearchParameter | Custom search params with auto-created DB indexes |
| CodeSystem / ValueSet | Terminology for validation bindings |
| ConceptMap | Code translation mappings |
| ImplementationGuide | Package of all above for a use case |

### Loading IGs

Three methods:

```bash
# 1. FHIR Package API (pull from package registry)
POST /fhir/ImplementationGuide/$load
{"id": "hl7.fhir.us.core", "version": "6.1.0"}

# 2. CLI tool
uploadfig --package hl7.fhir.us.core#6.1.0 --url http://localhost:8080

# 3. Environment variable at startup
AIDBOX_FHIR_PACKAGES=hl7.fhir.us.core#6.1.0,hl7.fhir.us.davinci-hrex#1.0.0

# 4. Init Bundle (infrastructure-as-code)
# Reference package in FHIR Bundle loaded at startup
```

### Validation modes

| Mode | Behavior | Use |
|---|---|---|
| Synchronous (default) | Validate on write; returns errors immediately; request fails if invalid | Greenfield apps, clean data |
| Asynchronous | Accept first, validate in background; poll for status | Migration from legacy systems with imperfect data |
| Skip reference validation | `x-fhir-skip-reference-validation: true` header | Migration when referenced resources don't exist yet |

### Defining custom resources (two approaches)

**Using FHIR Schema (recommended):**
```json
{
  "resourceType": "FHIRSchema",
  "id": "CustomAppointment",
  "name": "CustomAppointment",
  "url": "http://example.com/StructureDefinition/CustomAppointment",
  "type": "CustomAppointment",
  "base": "DomainResource",
  "elements": {
    "patientId": {"type": "string", "required": true},
    "scheduledAt": {"type": "dateTime", "required": true}
  }
}
```

**Using StructureDefinition:**
Standard FHIR StructureDefinition with `kind: resource` and `derivation: specialization`.

---

## 15. Subscriptions & Event Streaming

### FHIR topic-based subscriptions

Three variants depending on your FHIR version:
- R5: `SubscriptionTopic` + `Subscription` (native)
- R4B: Backport IG (R4B Subscription resource)
- R4: Backport IG (R4 Subscription resource)

### AidboxTopicSubscription

Aidbox's extended subscription model with more destination types than standard FHIR. Uses `AidboxTopicSubscription` resource.

```json
{
  "resourceType": "AidboxTopicSubscription",
  "id": "patient-kafka",
  "topic": "http://example.com/topic/patient-changes",
  "destination": {
    "type": "kafka",
    "endpoint": "kafka:9092",
    "topic": "patient-events"
  }
}
```

### SubSubscriptions

Aidbox SubSubscriptions allow subscribing to a subset of events from an existing SubscriptionTopic with additional filter criteria — useful when multiple consumers need different slices of the same event stream.

---

## 16. Integration Toolkit

### Supported standards

| Standard | Capability | Deployment |
|---|---|---|
| HL7 v2 | Parse & transform v2 messages → FHIR resources | Sidecar listener or built-in HL7v2 module |
| C-CDA | Bidirectional: C-CDA ↔ FHIR document conversion | Separate C-CDA converter microservice |
| X12 | Parse X12 EDI messages (claims, eligibility) | Converter module |
| Apple HealthKit | Import HealthKit medical records as FHIR | Built-in adapter |

### C-CDA converter

- Deploy as a separate microservice alongside Aidbox
- Supports custom conversion rules for non-standard C-CDA implementations
- Can produce C-CDA documents from FHIR resources (e.g., for regulatory reporting or EHR export)
- Supports 50+ C-CDA section templates (allergies, medications, vitals, procedures, etc.)

### HL7 v2 integration

Two approaches:
1. **New HL7v2 module** (`modules/other-modules/hl7v2`) — built-in, FHIR-resource-based configuration
2. **Legacy integration toolkit** — TCP listener with lisp/mapping DSL for transformation

The new module supports FHIR-native configuration via `HL7v2Config` resources and automatic message lifecycle management.

### Mappings module

General-purpose data transformation DSL for custom integration scenarios where standard adapters don't apply.

### Analytics integrations

Direct PostgreSQL access, SQL on FHIR views, and specific connectors:
- Tableau — via PostgreSQL connector to SQL on FHIR views
- Power BI — documented connector setup
- Jupyter — direct PostgreSQL / `/$sql` endpoint
- dbt — compatible with SQL on FHIR views as sources

### Email providers

Integrated email notification support via SMTP, Mailgun, Postmark, SendGrid. Configure via `EmailProvider` resource and send via `Notification` resource.

---

## 17. SQL on FHIR

Implements the HL7 SQL on FHIR v2 specification. Flattens nested FHIR resources into tabular PostgreSQL views optimized for analytics.

### ViewDefinition basics

```json
{
  "resourceType": "ViewDefinition",
  "name": "patient_demographics",
  "resource": "Patient",
  "status": "active",
  "select": [
    {
      "column": [
        {"name": "id", "path": "getResourceKey()"},
        {"name": "gender", "path": "gender"},
        {"name": "birth_date", "path": "birthDate"}
      ]
    },
    {
      "forEach": "name.where(use = 'official').first()",
      "column": [
        {"name": "family_name", "path": "family"},
        {"name": "given_names", "path": "given.join(' ')"}
      ]
    }
  ]
}
```

Creates a PostgreSQL view at `sof.patient_demographics`.

### Key FHIRPath expressions

| Expression | Result |
|---|---|
| `getResourceKey()` | Resource id |
| `name.where(use='official').first().family` | Official last name |
| `given.join(' ')` | Given names concatenated |
| `telecom.where(system='email').value` | Email address |
| `extension.where(url='...').value.ofType(CodeableConcept)` | Extension value |

### forEach — expanding arrays

```json
{"forEach": "name", "column": [
  {"name": "use", "path": "use"},
  {"name": "family", "path": "family"}
]}
```

Creates one row per name entry per patient — essential for one-to-many relationships.

### Operations

| Operation | Endpoint | Purpose |
|---|---|---|
| `$run` | `POST /ViewDefinition/[id]/$run` | Execute view against current data |
| `$materialize` | `POST /ViewDefinition/[id]/$materialize` | Materialize view to a physical table |

### Cross-resource analytics

```sql
-- COVID-19 cohort with lab values
SELECT p.family_name, p.birth_date, o.value_quantity
FROM sof.patient_demographics p
JOIN sof.condition_summary c ON c.patient_id = p.id
JOIN sof.observation_vitals o ON o.patient_id = p.id
WHERE c.code = '840539006'   -- COVID-19 SNOMED
  AND o.code = '89579001';
```

Connect Tableau or Power BI directly to PostgreSQL and query `sof.*` views as regular tables.

---

## 18. AI & MCP Tools

> **Status:** Alpha. Available from Aidbox v2505. `validate-fhir-resource` tool added in v2509.

### What the MCP server does

The Aidbox MCP server is an SSE-based service that exposes FHIR CRUD operations as typed tools any MCP-compliant LLM can discover and invoke — a standards-based bridge between an AI agent and your FHIR store, no custom integration code required on the LLM side.

### Server endpoints

| Endpoint | Purpose |
|---|---|
| `<base-url>/mcp` | SSE connection — client connects here to discover tools |
| `<base-url>/mcp/<client-id>/messages` | Message channel — LLM sends tool calls here |

### Available MCP tools

| Tool | Key parameters | Description |
|---|---|---|
| `read-fhir-resource` | resourceType, id | Read a single resource by ID |
| `create-fhir-resource` | resourceType, resource (JSON), headers | Create a new resource |
| `update-fhir-resource` | resourceType, id, resource (JSON) | Full replace of existing resource |
| `patch-fhir-resource` | resourceType, id, resource (JSON) | Partial update |
| `conditional-update-fhir-resource` | resourceType, resource, query | Update by search criteria |
| `conditional-patch-fhir-resource` | resourceType, resource, query | Patch by search criteria |
| `delete-fhir-resource` | resourceType, id | Delete (soft delete) |
| `search-fhir-resources` | resourceType, query | FHIR search with any valid query string |
| `validate-fhir-resource` *(v2509+)* | resourceType, resource, mode | Validate against active profiles |

### Enable MCP server

**One-liner (local dev):**
```bash
curl -JO https://aidbox.app/runme/mcp && docker compose up
```
Spins up Aidbox with MCP enabled and a permissive AccessPolicy pre-created.

**Existing Aidbox:**
```
module.mcp.server-enabled=true
```
Then create an AccessPolicy covering operations: `mcp`, `mcp-sse`, `mcp-client-messages`.

### Access control for MCP

**Option 1 — Public (local dev only, never with real data):**
```json
{
  "resourceType": "AccessPolicy",
  "id": "allow-mcp-endpoints",
  "link": [
    {"id": "mcp", "resourceType": "Operation"},
    {"id": "mcp-sse", "resourceType": "Operation"},
    {"id": "mcp-client-messages", "resourceType": "Operation"}
  ],
  "engine": "allow"
}
```

**Option 2 — Client credentials (recommended):**

```json
// 1. Create client
PUT /Client/mcp-client
{
  "id": "mcp-client",
  "secret": "change-this-secret",
  "grant_types": ["client_credentials"]
}

// 2. Create scoped AccessPolicy
PUT /AccessPolicy/mcp-endpoints
{
  "engine": "matcho",
  "matcho": {
    "client": {"id": "mcp-client"},
    "operation": {
      "$one-of": [
        {"resourceType": "Operation", "id": "mcp"},
        {"resourceType": "Operation", "id": "mcp-sse"},
        {"resourceType": "Operation", "id": "mcp-client-messages"}
      ]
    }
  }
}

// 3. Get token
POST /auth/token
{
  "client_id": "mcp-client",
  "client_secret": "change-this-secret",
  "grant_type": "client_credentials"
}
```

### Connecting LLM agents

Aidbox's MCP server speaks SSE. Tools expecting stdio MCP need `supergateway` as a bridge:

**Claude Code (CLI):**
```bash
claude mcp add aidbox-mcp -- npx -y supergateway --sse http://localhost:8080/mcp
```

**Claude Desktop / ChatGPT Desktop:**
```json
{
  "mcpServers": {
    "aidbox": {
      "command": "npx",
      "args": [
        "-y", "supergateway",
        "--sse", "https://your-aidbox.example.com/mcp",
        "--oauth2Bearer", "YOUR_TOKEN_HERE"
      ]
    }
  }
}
```
Place in `Settings → Developer → Edit Config` (Claude Desktop) or `.cursor/mcp.json` (Cursor).

> **Node version note:** Claude Desktop requires Node 18+. Uninstall older nvm versions (`nvm uninstall v16` etc.) and run `nvm cache clear`.

**Cursor editor:** Add config to `.cursor/mcp.json` and enable MCP in Cursor Settings → Cursor Settings → MCP.

### MCP Inspector (test & discover)

```bash
npx @modelcontextprotocol/inspector
# Open http://localhost:6274
# Transport Type: SSE
# URL: http://localhost:8080/mcp
# Add bearer token under Authentication if using secured endpoint
```

Lets you browse all available tools, inspect schemas, and run test calls without writing code.

### AI Prompts

Aidbox ships pre-built prompt templates (Tutorials → Other Tutorials → AI Prompts) for:
- Natural language → FHIR search query translation
- Synthetic test data generation for clinical scenarios
- Resource validation against named profiles
- Exploring available resource types and SearchParameters
- Generating StructureDefinitions from plain-English descriptions

### Formbox AI assistant

The Formbox (forms module) includes a dedicated AI Assistant in its Form Builder UI — separate from the MCP server. Generates `Questionnaire` structure from natural-language descriptions, useful for clinical form authors who don't want to hand-code FHIR SDC.

### Security considerations for AI access

| Risk | Mitigation |
|---|---|
| LLM accidentally deletes/overwrites patient data | Create a read-only AccessPolicy for the MCP client; restrict to GET operations only |
| Token leakage in LLM logs or traces | Use short-lived client credentials tokens; rotate regularly |
| Prompt injection via FHIR resource content | Sanitize patient-supplied text before embedding in LLM prompts |
| Unintended data exposure in AI context window | Limit `search-fhir-resources` result sizes via `_count`; apply resource-level AccessPolicies |

**Never use the public (allow-all) AccessPolicy in any environment with real patient data.**

---

## 19. SDKs & Developer Tooling

### Official SDKs

| Language | Features |
|---|---|
| TypeScript | Typed FHIR resource models, REST client, code generation |
| Python | FHIR resource classes, async support, search builders |
| C# / .NET | FHIR.NET-compatible models, CRUD client |
| Java | HAPI FHIR-compatible integration layer |

### Code generation

Aidbox's codegen tool generates strongly-typed FHIR models from any loaded StructureDefinition. Load US Core IG → get TypeScript interfaces for all US Core profiles automatically.

### Aidbox Apps — plugin pattern

Register any HTTP service as an Aidbox App to extend functionality. Aidbox calls your service for custom operations, subscription handling, or data transformation. Any language, any runtime.

```json
{
  "resourceType": "App",
  "id": "my-custom-app",
  "type": "app",
  "baseUrl": "http://my-service:3000",
  "endpoint": {
    "my-operation": {
      "method": "POST",
      "path": ["/my-operation"]
    }
  }
}
```

### Aidbox UI tools

| Tool | Purpose |
|---|---|
| REST Console | Interactive FHIR REST requests from the UI |
| Database Console | Direct SQL query execution against PostgreSQL |
| Aidbox Notebooks | Collaborative FHIR + SQL exploration |
| Attrs Stats | Analyze which fields are actually populated across resources |
| DB Tables | Browse raw table structure |
| DB Queries | Saved SQL queries for the team |
| FHIR Viewer | Browse and search resources with UI |

### Init Bundle

A FHIR Bundle loaded at Aidbox startup containing AccessPolicies, Clients, Users, IGs, and other meta-resources. Enables infrastructure-as-code for Aidbox configuration — commit your entire Aidbox config to git.

```bash
# Inject environment variables into Init Bundle
AIDBOX_INIT_BUNDLE_PATH=/path/to/init-bundle.json
```

### React integration

Aidbox provides React hooks and utilities for FHIR-aware frontends — handles authentication flow, resource fetching, and subscription updates.

---

## 20. Deployment & Operations

### Configuration

All configuration via environment variables. Sensitive values use external secret files (mounted volumes) — never put secrets in env vars in production.

```bash
# Essential environment variables
AIDBOX_LICENSE=your-license-key
PGHOST=postgres
PGPORT=5432
PGDATABASE=aidbox
PGUSER=aidbox
PGPASSWORD=secret
AIDBOX_BASE_URL=https://your-domain.com
AIDBOX_PORT=8080

# Enable FHIR Schema validation
BOX_FEATURES_FHIR_SCHEMA_VALIDATION=true

# Load IGs at startup
AIDBOX_FHIR_PACKAGES=hl7.fhir.us.core#6.1.0

# MCP server
module.mcp.server-enabled=true
```

### Kubernetes deployment

```yaml
# Key points:
# - Aidbox container is stateless → scale replicas horizontally
# - Single PostgreSQL primary (or managed DB service)
# - Add read replica for analytics/heavy read workloads
# - Health check: GET /health
# - Readiness probe: GET /ready
```

Deploy with Helm charts (official charts available). For HA: multiple Aidbox replicas + primary + read replicas.

### Managed PostgreSQL compatibility

AWS RDS PostgreSQL, Google Cloud SQL, Azure Database for PostgreSQL, self-hosted, on-premises.

### Backup & restore

Standard PostgreSQL backup strategies:
- `pg_dump` — logical backup, portable
- `pg_basebackup` — physical backup, faster restore
- WAL-G — continuous WAL archiving, point-in-time recovery
- Crunchy pgBackRest — K8s-native backup operator

Also: Aidbox Archive/Restore API moves old resources to cold storage (S3/GCS) while keeping the DB lean.

### External secrets

Mount secret files instead of env vars for credentials:

```bash
AIDBOX_SECRET_FILES=/secrets/db-password:/run/secrets/db_password
```

Integrates with:
- Azure Key Vault
- HashiCorp Vault

### Migrations

Schema migrations managed automatically by Aidbox on startup. When loading new FHIR packages or StructureDefinitions, Aidbox updates the DB schema without manual scripts. For custom data migrations (renaming fields, backfilling): use the Migrations API.

### Index management

```
GET /Indexes/$suggest    # Get recommended indexes based on query patterns
POST /Indexes/$create    # Create suggested or custom indexes
```

Review and rebuild indexes after large data loads. The Indexes module monitors index health and can suggest missing indexes based on slow query patterns.

### File storage

Binary/attachment storage (for FHIR `Binary` resources and document attachments):

| Cloud | Notes |
|---|---|
| AWS S3 | Presigned URL support |
| GCP Cloud Storage | Service account auth |
| Azure Blob Storage | Connection string or managed identity |
| Oracle Cloud Storage | OCI auth |

---

## 21. Observability

### Three pillars

| Pillar | Endpoint/Protocol | Destinations |
|---|---|---|
| Logs | Stdout (JSON), OTEL logs exporter | Grafana Loki, Datadog, CloudWatch, Elastic, any OTEL collector |
| Metrics | `GET /metrics` (Prometheus), OTEL metrics exporter | Prometheus + Grafana, Datadog, any OTEL collector |
| Traces | OTEL traces exporter | Jaeger, Zipkin, any OTLP-compatible backend |

### OpenTelemetry setup (local dev)

```bash
curl -JO https://aidbox.app/runme/otel && docker compose up
# Includes Aidbox + OTEL collector + Grafana
```

### Key Prometheus metrics

| Category | Examples |
|---|---|
| HTTP | Request rate, latency histograms (p50/p95/p99), error rate by status code |
| Database | Query duration, connection pool usage, slow query count |
| FHIR | Operations by resource type, validation error rate |
| System | JVM heap, thread count, GC pressure |

### Extending logs

Add custom fields to Aidbox log events via log hooks — useful for application-specific audit trails or correlation IDs.

### FHIR Audit logging

FHIR Basic Audit Logging Profile (BALP): every API operation creates an `AuditEvent` resource.

```
GET /fhir/AuditEvent?agent-name=johndoe&date=gt2024-01-01
```

Fields captured: `who` (agent), `what` (resource), `when` (recorded), `action` (C/R/U/D/E), `outcome`.

---

## 22. Multitenancy

### Two models

| Model | Description | Best for |
|---|---|---|
| Multibox | Single Aidbox + single PostgreSQL; logical tenant isolation via policies | SaaS with many small tenants |
| Full instance isolation | Separate Aidbox + PostgreSQL per tenant | Few large enterprise tenants with strict data segregation |

### Scoped APIs

| API | Context enforced |
|---|---|
| Patient API | All requests scoped to specific patient's compartment |
| Organization API | All requests scoped to an organization's resources |
| Compartment API | FHIR-defined compartments (Patient, Practitioner, Encounter, Device) |

### Common SaaS pattern

Multibox + Organization-scoped access policies:

1. Each tenant authenticates with org-specific Client credentials
2. AccessPolicy restricts visibility to `resource.organization = token.organization`
3. All resources tagged with organization reference on creation

### Hierarchical access control

When org hierarchy matters (system → hospital → department → ward), the hierarchical AC module can propagate access rights down the tree automatically.

---

## 23. Decision Guide

### Which API?

| Scenario | Use |
|---|---|
| External SMART app or partner integration | FHIR REST at `/fhir/*` |
| Internal microservice, performance-critical | Aidbox REST at `/*` |
| Frontend with flexible data needs | GraphQL at `/$graphql` |
| Analytics dashboard or BI tool | SQL on FHIR views or `/$sql` |
| Natural language / AI agent access to FHIR | MCP server |
| Batch data import from legacy system | `$import` or `$load` |
| Real-time event notification | FHIR Subscriptions |
| ETL sync pipeline | Changes API (cursor-based polling) |
| Create multiple linked resources atomically | Transaction Bundle |
| Validate without writing | `POST /[type]/$validate` |

### Which auth flow?

| Scenario | Flow |
|---|---|
| Web app with user login | Authorization Code |
| Backend service / machine-to-machine | Client Credentials |
| SMART EHR app launch | SMART on FHIR (Authorization Code + launch context) |
| Patient portal | SMART standalone launch |
| External token validation | Token Introspection |
| Delegated access | Token Exchange |

### Which multitenancy model?

| Scenario | Use |
|---|---|
| SaaS, many small tenants | Multibox + Organization-scoped policies |
| Few large enterprise tenants | Separate Aidbox instances per tenant |
| Patient portal (patient sees own data only) | Patient-scoped API + SMART on FHIR |
| Multi-clinic, hierarchical org structure | Hierarchical access control module |

### Custom resources — when?

Prefer modeling in **standard FHIR resources** whenever possible — maximizes interoperability and IG reuse. Use custom resources only when:
- The domain concept has no FHIR equivalent
- The entity is unlikely to be needed by external systems
- You've verified no FHIR extension pattern suffices

### Validation strategy

| Scenario | Approach |
|---|---|
| Greenfield — clean data from the start | Synchronous (default) |
| Data migration from legacy system | Async validation + `x-fhir-skip-reference-validation` header |
| High-volume ingestion where speed matters | `$load` with reduced validation, remediate after |
| Third-party FHIR data (variable quality) | Async validation + monitoring dashboard |

### Subscription channel choice

| Destination | Use |
|---|---|
| Custom HTTP endpoint | `rest-hook` |
| Real-time UI | `websocket` |
| Kafka | `AidboxTopicDestination` (kafka type) |
| AWS | SNS or EventBridge `AidboxTopicDestination` |
| GCP | Pub/Sub `AidboxTopicDestination` |
| Simple polling ETL | Changes API instead |

### Index decisions

| Query pattern | Index type |
|---|---|
| FHIR search via registered SearchParameter | Auto-created GIN index |
| Direct SQL `@>` containment | GIN index on `resource` column |
| Extracted path (e.g. `resource->>'birthDate'`) | Expression index |
| Full-text search | GIN with `pg_trgm` |

---

## 24. Deprecated Patterns to Avoid

The following are documented in Aidbox but should **not** be used in new development:

| Deprecated | Replacement |
|---|---|
| Zen-lang configuration project | Environment variables + Init Bundle |
| Zen-lang validator | FHIR Schema validator |
| Entity/Attribute model | StructureDefinition / FHIR Schema |
| AidboxProfile resources | StructureDefinition |
| FHIR Terminology Repository (FTR) | Load IGs via environment variable or FHIR API |
| Zen SearchParameters | FHIR SearchParameter resources |
| ACL (Access Control Lists) | AccessPolicy with Matcho DSL |
| SMARTbox (deprecated) | Aidbox + FHIR App Portal |
| GCP Pub/Sub (deprecated integration) | AidboxTopicDestination with pub-sub type |
| AidboxDB (deprecated container) | Standard PostgreSQL |
| Implicit OAuth grant | Authorization Code with PKCE |
| Legacy Workflow Engine (Zen-based) | Aidbox Apps + external workflow engines |
| Old MDM module | MDMbox / MDM module under `modules/mdm` |
| Aidbox SDK (deprecated) | Current SDKs: TypeScript, Python, C#, Java |

> If you encounter Zen-lang namespaces, `.edn` config files, or `AidboxProfile` resources in existing code, those are legacy patterns from the pre-2024 Aidbox configuration approach. Migrate to StructureDefinition + FHIR Schema.

---

## Reference Links

| Resource | URL |
|---|---|
| Documentation home | https://www.health-samurai.io/docs/aidbox |
| Architecture | https://www.health-samurai.io/docs/aidbox/architecture |
| Database overview | https://www.health-samurai.io/docs/aidbox/database/overview |
| API overview | https://www.health-samurai.io/docs/aidbox/api/api-overview |
| Access control | https://www.health-samurai.io/docs/aidbox/access-control/access-control |
| MCP module | https://www.health-samurai.io/docs/aidbox/modules/other-modules/mcp |
| AI prompts | https://www.health-samurai.io/docs/aidbox/tutorials/other-tutorials/ai-prompts |
| SQL on FHIR | https://www.health-samurai.io/docs/aidbox/modules/sql-on-fhir |
| All settings reference | https://www.health-samurai.io/docs/aidbox/reference/all-settings |
| FHIR Schema reference | https://fhir-schema.github.io/fhir-schema/ |
| GitHub examples | https://github.com/Aidbox/examples |
| Zulip community | https://connect.health-samurai.io/ |
| Release notes | https://www.health-samurai.io/docs/aidbox/overview/release-notes |
