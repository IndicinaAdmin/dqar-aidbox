# Source-Type Inference Algorithm
**DQAR Shared Knowledge Base — Domain 3 / UC1 Pipeline**
*Version: June 2026 v2 | Used by: UC1 Assessment App, UC3, UC4, UC5*

---

## Purpose

When a client FHIR extract carries no `meta.source` URI and no Provenance resources, the UC1 ingest pipeline cannot directly read the originating source system type. This algorithm infers source-type and source-system-id from FHIR resource structure using signals that US Core 6.1.0 conformance requires to be present.

**The inference result drives five AuditEvent extension fields (EXT 1–5):**
- `http://Sonian.io/fhir/ext/source-type` (EXT 1)
- `http://Sonian.io/fhir/ext/source-system-id` (EXT 2)
- `http://Sonian.io/fhir/ext/source-feed-id` (EXT 3)
- `http://Sonian.io/fhir/ext/source-inference-confidence` (EXT 4)
- `http://Sonian.io/fhir/ext/ecds-ssor` (EXT 5) ← derived from source-type via SSoR mapping rule

**EXT 6 (`ingest-pipeline-id`) and EXT 7 (`ol-run-id`) are set by the pipeline orchestrator at run time — not derived by this algorithm.** EXT 7 is an ingest batch tag (OpenLineage run ID UUID), not a join key — OpenLineage RunEvents go directly to OpenMetadata (Marquez dropped), which builds the lineage graph from each RunEvent's declared inputs/outputs; required for DQAR provenance maturity Level 3+.

---

## Source-Type Vocabulary — Expanded

The source-type vocabulary is layered into two tiers based on what the algorithm can detect from FHIR resource signals alone versus what requires explicit declaration in the feed manifest or `meta.source`.

### Tier A — Structurally detectable (Priorities 3–6 can resolve without manifest)

| source-type | Description | Primary signal |
|---|---|---|
| `clinical_ehr` | EHR clinical data | SNOMED codes + verificationStatus + recorder + rich Encounter participants; vital-signs/exam/survey Observation categories |
| `administrative_claims` | Claims / adjudicated data | ExplanationOfBenefit, Claim, ClaimResponse (determinative); ICD-10-only Condition |
| `administrative_encounter` | Encounter-based administrative | CPT-coded Encounter with no participants |
| `pharmacy_pbm` | PBM pharmacy dispensing | MedicationDispense (determinative); known PBM identifier system URIs |
| `clinical_lab` | Laboratory results | Observation.category = `laboratory` (US Core MUST SUPPORT — not inference, a declaration) |
| `payer_exchange` | P2P data from another payer | PDex meta.profile; Provenance with payer agent type; PDex-specific resource patterns |
| `clinical_immunization_registry` | Immunization registry (IIS) data | `Immunization.primarySource = false` (US Core MUST SUPPORT field — false means data reported from another source, typically a state IIS) |

### Tier B — Manifest/meta.source declared only (structural signals cannot distinguish these)

| source-type | Description | Why structurally indistinguishable | Governance implication |
|---|---|---|---|
| `clinical_phr` | Patient-facing app / PHR data | FHIR resource structure identical to EHR data | Requires `meta.source` URI or manifest declaration |
| `pharmacy_specialty` | Specialty pharmacy dispensing | MedicationDispense — only identifier system URI distinguishes from PBM | Requires known specialty pharmacy URI list in manifest |
| `clinical_hie` | HIE-aggregated clinical data | Condition/Observation structurally identical to EHR | Requires `meta.source` URI (CommonWell, Carequality) or manifest |
| `clinical_registry` | Clinical registry data | Structurally identical to EHR data | Requires `meta.source` URI or manifest |
| `case_management` | Case management program data | Condition/Encounter structurally identical to EHR | Manifest only — no structural signal |
| `disease_management` | Disease management program data | Condition/Encounter structurally identical to EHR | Manifest only — no structural signal |

**Tier B types defaulting to `unknown` are a Tier 1 governance finding.** If a plan has case management or disease management data flowing into their FHIR pipeline without feed manifest declaration and without `meta.source` population, the algorithm cannot classify it. That `unknown` is direct evidence of a metadata management governance gap — the algorithm's limitation proves the finding. The feed manifest discipline required to make Tier B types resolvable is precisely the DAMA-BOK metadata management capability assessed in Track B Level 6.

---

## Vocabulary-to-SSoR Mapping Rule

NCQA ECDS SSoR (Source of Record) has four categories. The mapping from source-type to SSoR is a deterministic rule — no inference required.

```python
SOURCE_TYPE_TO_SSOR = {
    # EHR/PHR
    'clinical_ehr':              'EHR/PHR',
    'clinical_phr':              'EHR/PHR',
    'payer_exchange':            'EHR/PHR',     # P2P data originates from payer EHR/claims mix

    # Administrative
    'administrative_claims':     'Administrative',
    'administrative_encounter':  'Administrative',
    'pharmacy_pbm':              'Administrative',
    'pharmacy_specialty':        'Administrative',

    # Clinical Registry/HIE
    'clinical_lab':                       'Clinical Registry/HIE',
    'clinical_hie':                       'Clinical Registry/HIE',
    'clinical_registry':                  'Clinical Registry/HIE',
    'clinical_immunization_registry':     'Clinical Registry/HIE',

    # Case/Disease Mgmt
    'case_management':           'Case/Disease Mgmt',
    'disease_management':        'Case/Disease Mgmt',

    # Unresolvable — triggers finding
    'unknown':                    None,          # SSoR not attributable — Tier 1 governance finding
}
```

---

## Why Inference Is Tractable in US Core

US Core 6.1.0 mandates `Observation.category` as a MUST SUPPORT element. This single design decision makes source-type inference reliable for the most clinically significant resources. The category code is the primary discriminator — it was designed exactly to tell consuming systems what kind of observation this is without parsing the code itself.

The US Core profile set is organized around this: there is not one Observation profile but many, each with a fixed category constraint. When a FHIR server produces a valid US Core Observation, it has already declared its category, which means the inference algorithm does not infer — it reads.

Inference only becomes probabilistic for Condition, Encounter, and Procedure, where the profile does not distinguish clinical from administrative origin. Tier B types (PHR, HIE, registry, case management, disease management) are structurally indistinguishable from `clinical_ehr` at the resource level — they require feed manifest or `meta.source` declaration.

---

## Priority 1 — Feed Manifest (asserted confidence)

Before applying any inference, check whether the resource can be matched to a declared feed in the client-provided feed manifest.

```python
def get_source_from_manifest(resource, feed_manifest):
    """
    Match resource to feed manifest entry.
    Returns (source_type, feed_id, confidence='asserted') or None.
    """
    filename = resource.get('_source_file')  # set by ingest pipeline
    if not feed_manifest or not filename:
        return None
    for feed in feed_manifest.get('feeds', []):
        if filename in feed.get('files', []):
            return {
                'source_type': feed['source_system_type'],
                'source_feed_id': feed['feed_id'],
                'confidence': 'asserted'
            }
    # File not declared in manifest
    return {
        'source_type': 'unknown',
        'source_feed_id': f"undeclared-{filename}",
        'confidence': 'unknown',
        'finding': 'UNDECLARED_SOURCE'  # triggers finding generation
    }
```

---

## Priority 2 — meta.source URI (asserted confidence)

Priority 2 is the primary resolution path for Tier B source types. A well-populated `meta.source` URI can resolve all twelve source types including those structurally indistinguishable from `clinical_ehr`.

```python
def get_source_from_meta(resource):
    """
    Derive source-type from meta.source URI if present.
    Returns (source_type, source_system_id, confidence='asserted') or None.
    Resolves all Tier A and Tier B source types.
    """
    meta_source = resource.get('meta', {}).get('source')
    if not meta_source:
        return None

    uri = meta_source.lower()

    # Tier B — must be detected here; structural inference cannot distinguish
    if any(k in uri for k in ['phr', 'myhealth', 'patient-app', 'personal-health']):
        source_type = 'clinical_phr'
    elif any(k in uri for k in ['commonwell', 'carequality', 'hie', 'health-information-exchange', 'rhio']):
        source_type = 'clinical_hie'
    elif any(k in uri for k in ['registry', 'clinical-registry', 'oncology-registry', 'cardiac-registry']):
        source_type = 'clinical_registry'
    elif any(k in uri for k in ['case-management', 'case_management', 'care-management', 'casemanagement']):
        source_type = 'case_management'
    elif any(k in uri for k in ['disease-management', 'disease_management', 'dm-program', 'chronic-care']):
        source_type = 'disease_management'

    # Tier A — also resolvable from meta.source with higher specificity
    elif any(k in uri for k in ['specialty-pharmacy', 'specialty_pharmacy', 'biologics', 'accredo', 'cvs-specialty']):
        source_type = 'pharmacy_specialty'
    elif any(k in uri for k in ['pharmacy', 'pbm', 'rxclaim', 'medco', 'express-scripts', 'caremark', 'optumrx']):
        source_type = 'pharmacy_pbm'
    elif any(k in uri for k in ['quest', 'labcorp', 'lab', 'pathology', 'lims', 'laboratory']):
        source_type = 'clinical_lab'
    elif any(k in uri for k in ['p2p', 'pdex', 'payer-exchange', 'payer_exchange', 'interopability']):
        source_type = 'payer_exchange'
    elif any(k in uri for k in ['claims', 'edw', 'adjudic', 'eob', 'billing', 'administrative']):
        source_type = 'administrative_claims'
    elif any(k in uri for k in ['encounter', 'visit', 'facility-encounter']):
        source_type = 'administrative_encounter'
    elif any(k in uri for k in ['epic', 'cerner', 'meditech', 'allscripts', 'athena', 'ehr', 'emr', 'clinical']):
        source_type = 'clinical_ehr'
    else:
        source_type = 'clinical_ehr'  # default for unrecognized URIs — asserted but less specific

    import hashlib
    source_id = 'meta-' + hashlib.sha256(meta_source.encode()).hexdigest()[:12]

    return {
        'source_type': source_type,
        'source_feed_id': source_id,
        'source_system_id': source_id,
        'confidence': 'asserted'
    }
```

---

## Priority 2.5 — identifier.system URI (asserted confidence)

Between `meta.source` and determinative resource types. Applies to any FHIR resource that carries an `identifier[]` array.

**Why this priority exists:**

PHI redaction in `dqar-client-kit` hashes `identifier.value` but preserves `identifier.system` intact. The system URI is a namespace declaration by the originating source system — it is not patient-identifying. It survives the redaction boundary and arrives in the egress package as an authoritative signal for which source system produced the resource.

This is the primary resolution path for `source_system_id` (EXT 2) in extracts where `meta.source` is not populated. For most Encounters from EHR systems, the `identifier.system` URI names the originating EHR (Epic, Athena, Cerner). Two resources from the same source system share an identical `identifier.system` URI and therefore hash to the same `source_system_id` — enabling stable grouping in risk stratification.

**Source-type resolution:**

The same URI pattern matching used in Priority 2 (`meta.source`) is applied to `identifier.system`. This allows Priority 2.5 to resolve Tier B types when the identifier system URI is an explicit declaration (e.g. `https://commonwell.org/patient-id` → `clinical_hie`).

**Non-informative systems are filtered:**

Synthetic or placeholder URIs (`http://example.org/mrn`, Synthea, `urn:ietf:rfc:3986`) are excluded before pattern matching. Resources with only non-informative identifier systems fall through to Priority 3.

**Confidence:**
- URI pattern recognized → `asserted`
- URI present and non-filtered but pattern unrecognized → `medium` (EHR default; system URI preserved as `source_system_id`)

```python
def get_source_from_identifier_system(resource):
    """
    Priority 2.5: identifier.system URI → source_system_id + source_type.
    Non-informative systems (example.org, Synthea, etc.) are skipped.
    First informative URI wins.
    """
    for ident in resource.get('identifier', []):
        system = ident.get('system', '')
        if not system or is_non_informative(system):
            continue
        source_type = _uri_to_source_type(system)
        sys_id = 'id-sys-' + sha256(system)[:12]
        if source_type:
            return {'source_type': source_type, 'source_system_id': sys_id,
                    'source_feed_id': sys_id, 'confidence': 'asserted',
                    'inference_basis': f'identifier.system={system}'}
        return {'source_type': 'clinical_ehr', 'source_system_id': sys_id,
                'source_feed_id': sys_id, 'confidence': 'medium',
                'inference_basis': f'identifier.system={system} (unrecognized-pattern → clinical_ehr default)'}
    return None
```

---

## Priority 3 — Resource Type Inference (high confidence)

Determinative resource types require no signal beyond `resourceType`. These are Tier A types — structurally unambiguous.

```python
DETERMINATIVE_RESOURCE_TYPES = {
    'ExplanationOfBenefit': ('administrative_claims',          'high'),
    'Claim':                ('administrative_claims',          'high'),
    'ClaimResponse':        ('administrative_claims',          'high'),
    'Coverage':             ('administrative_claims',          'high'),
    'MedicationDispense':   ('pharmacy_pbm',                   'high'),  # refined to pharmacy_specialty
                                                                          # at Priority 2 if meta.source present
    'Immunization':         ('clinical_immunization_registry', 'high'),  # refined to clinical_ehr
                                                                          # if primarySource=true/absent
}

def get_source_from_resource_type(resource):
    rt = resource.get('resourceType')
    if rt in DETERMINATIVE_RESOURCE_TYPES:
        source_type, confidence = DETERMINATIVE_RESOURCE_TYPES[rt]
        # Refine MedicationDispense: check identifier systems for specialty pharmacy URIs
        if rt == 'MedicationDispense':
            id_systems = [
                i.get('system', '').lower()
                for i in resource.get('identifier', [])
            ]
            specialty_signals = ['specialty', 'biologics', 'accredo', 'cvs-specialty',
                                  'walgreens-specialty', 'coram', 'bioscrip']
            if any(sig in sys for sys in id_systems for sig in specialty_signals):
                source_type = 'pharmacy_specialty'
        # Refine Immunization: primarySource=false → IIS registry; true or absent → EHR-captured
        if rt == 'Immunization':
            if resource.get('primarySource') is not False:
                source_type = 'clinical_ehr'
        return {
            'source_type': source_type,
            'confidence': confidence,
            'inference_basis': f'resourceType={rt}'
        }
    return None
```

---

## Priority 4 — Observation Category (high confidence)

US Core 6.1.0 requires `Observation.category` as MUST SUPPORT. Reading category is not inference — it is reading a required declaration. `laboratory` maps directly to `clinical_lab`; all other clinical categories map to `clinical_ehr`.

```python
OBSERVATION_CATEGORY_MAP = {
    'laboratory':     ('clinical_lab', 'high'),   # Clinical Registry/HIE → SSoR
    'vital-signs':    ('clinical_ehr', 'high'),
    'clinical-test':  ('clinical_ehr', 'high'),
    'exam':           ('clinical_ehr', 'high'),
    'survey':         ('clinical_ehr', 'high'),
    'social-history': ('clinical_ehr', 'high'),
    'activity':       ('clinical_ehr', 'high'),
    'imaging':        ('clinical_ehr', 'high'),
    'procedure':      ('clinical_ehr', 'high'),
    'therapy':        ('clinical_ehr', 'high'),
}

def get_source_from_observation_category(resource):
    if resource.get('resourceType') != 'Observation':
        return None
    categories = resource.get('category', [])
    for cat in categories:
        for coding in cat.get('coding', []):
            code = coding.get('code', '').lower()
            if code in OBSERVATION_CATEGORY_MAP:
                source_type, confidence = OBSERVATION_CATEGORY_MAP[code]
                return {
                    'source_type': source_type,
                    'confidence': confidence,
                    'inference_basis': f'Observation.category={code}'
                }
    return None
```

---

## Priority 5 — Secondary Signal Inference (medium confidence)

For Condition, Encounter, Procedure where resource type alone is not determinative. Note: this priority can only distinguish `clinical_ehr` from `administrative_claims` / `administrative_encounter`. It cannot resolve Tier B types — those remain `unknown` if not declared in manifest or `meta.source`.

```python
def get_source_from_secondary_signals(resource):
    rt = resource.get('resourceType')
    signals = []
    ehr_score = 0
    admin_score = 0

    if rt == 'Condition':
        codes = resource.get('code', {}).get('coding', [])
        systems = [c.get('system', '') for c in codes]
        has_snomed = any('snomed' in s.lower() for s in systems)
        has_icd10  = any('icd-10' in s.lower() or 'icd10' in s.lower() for s in systems)

        if has_snomed and not has_icd10:
            ehr_score += 2
            signals.append('SNOMED-only')
        elif has_icd10 and not has_snomed:
            admin_score += 2
            signals.append('ICD10-only')
        elif has_snomed and has_icd10:
            ehr_score += 1
            signals.append('dual-coded')

        vs = resource.get('verificationStatus', {}).get('coding', [{}])[0].get('code', '')
        if vs == 'confirmed':
            ehr_score += 2
            signals.append('verificationStatus=confirmed')
        elif not vs:
            admin_score += 1
            signals.append('verificationStatus=absent')

        if resource.get('onsetDateTime') or resource.get('onsetPeriod'):
            ehr_score += 1
            signals.append('onset-date-present')

        if resource.get('recorder'):
            ehr_score += 2
            signals.append('recorder-present')

    elif rt == 'Encounter':
        enc_types = resource.get('type', [])
        for et in enc_types:
            for coding in et.get('coding', []):
                system = coding.get('system', '').lower()
                if 'cpt' in system or 'hcpcs' in system:
                    admin_score += 2
                    signals.append('CPT-type-code')
                    break
                elif 'snomed' in system:
                    ehr_score += 2
                    signals.append('SNOMED-type-code')
                    break

        participants = resource.get('participant', [])
        if len(participants) > 1:
            ehr_score += 2
            signals.append(f'{len(participants)}-participants')
        elif len(participants) == 0:
            admin_score += 1
            signals.append('no-participants')

        if resource.get('location'):
            ehr_score += 1
            signals.append('location-present')

    elif rt == 'Procedure':
        codes = resource.get('code', {}).get('coding', [])
        systems = [c.get('system', '') for c in codes]
        has_snomed = any('snomed' in s.lower() for s in systems)
        has_cpt    = any('cpt' in s.lower() or 'hcpcs' in s.lower() for s in systems)

        if has_snomed:
            ehr_score += 2
            signals.append('SNOMED-procedure')
        if has_cpt and not has_snomed:
            admin_score += 1
            signals.append('CPT-only')

        if resource.get('performer'):
            ehr_score += 2
            signals.append('performer-present')

    else:
        return None

    if ehr_score == 0 and admin_score == 0:
        return None

    if ehr_score > admin_score:
        return {
            'source_type': 'clinical_ehr',
            'confidence': 'medium',
            'inference_basis': ', '.join(signals),
            'ehr_score': ehr_score,
            'admin_score': admin_score
        }
    elif admin_score > ehr_score:
        # Distinguish encounter vs claims by resource type
        source_type = 'administrative_encounter' if rt == 'Encounter' else 'administrative_claims'
        return {
            'source_type': source_type,
            'confidence': 'medium',
            'inference_basis': ', '.join(signals),
            'ehr_score': ehr_score,
            'admin_score': admin_score
        }
    else:
        # Tied score — default to ehr with lower confidence
        return {
            'source_type': 'clinical_ehr',
            'confidence': 'low',
            'inference_basis': f'tied-score: {", ".join(signals)}',
            'ehr_score': ehr_score,
            'admin_score': admin_score
        }
```
---

## Priority 6 — Topology Cluster (low confidence)

When no individual resource signals are available, group by structural fingerprint. Resources with identical fingerprints likely share origin. Note: topology clustering can only resolve Tier A types — it cannot distinguish Tier B types from `clinical_ehr`.

```python
import hashlib
import json

def compute_topology_fingerprint(resource):
    """
    Stable fingerprint from structural properties only.
    Does not include any patient data.
    """
    rt = resource.get('resourceType', '')

    code_systems = set()
    for coding in resource.get('code', {}).get('coding', []):
        if coding.get('system'):
            code_systems.add(coding['system'])

    id_systems = set()
    for identifier in resource.get('identifier', []):
        if identifier.get('system'):
            id_systems.add(identifier['system'])

    field_presence = {
        'has_meta_source':         bool(resource.get('meta', {}).get('source')),
        'has_recorder':            bool(resource.get('recorder')),
        'has_performer':           bool(resource.get('performer')),
        'has_participants':        bool(resource.get('participant')),
        'has_location':            bool(resource.get('location')),
        'has_onset':               bool(resource.get('onsetDateTime') or resource.get('onsetPeriod')),
        'has_verification_status': bool(resource.get('verificationStatus')),
        'category_codes': sorted([
            c.get('code', '')
            for cat in resource.get('category', [])
            for c in cat.get('coding', [])
        ]),
    }

    fingerprint_data = {
        'resource_type':      rt,
        'code_systems':       sorted(code_systems),
        'identifier_systems': sorted(id_systems),
        'field_presence':     field_presence,
    }

    fingerprint_str = json.dumps(fingerprint_data, sort_keys=True)
    return 'topology-' + hashlib.sha256(fingerprint_str.encode()).hexdigest()[:8]


def get_source_from_topology_cluster(resource, cluster_registry):
    fingerprint = compute_topology_fingerprint(resource)
    if fingerprint in cluster_registry:
        cluster = cluster_registry[fingerprint]
        return {
            'source_type': cluster['majority_source_type'],
            'source_feed_id': fingerprint,
            'confidence': 'low',
            'inference_basis': f'topology-cluster-{fingerprint}',
            'cluster_size': cluster['count'],
        }
    cluster_registry[fingerprint] = {
        'fingerprint': fingerprint,
        'resource_type': resource.get('resourceType'),
        'count': 1,
        'majority_source_type': 'unknown',
    }
    return {
        'source_type': 'unknown',
        'source_feed_id': fingerprint,
        'confidence': 'low',
        'inference_basis': f'new-topology-cluster-{fingerprint}',
    }
```

---

## Master Inference Function

```python
def infer_source_metadata(resource, feed_manifest=None, cluster_registry=None):
    """
    Run inference priorities in order. Return first successful result.
    Always returns a dict with source_type, source_feed_id,
    source_system_id, ecds_ssor, confidence, and inference_basis.
    EXT 6 (ingest-pipeline-id) and EXT 7 (ol-run-id) are set by
    the pipeline orchestrator and are not part of this return dict.
    """
    if cluster_registry is None:
        cluster_registry = {}

    # Priority 1: Feed manifest — resolves all Tier A and Tier B types
    result = get_source_from_manifest(resource, feed_manifest)
    if result and result['confidence'] != 'unknown':
        return _build_result(resource, result)

    # Priority 2: meta.source URI — resolves all Tier A and Tier B types
    result = get_source_from_meta(resource)
    if result:
        return _build_result(resource, result)

    # Priority 2.5: identifier.system URI — asserted source_system_id from identifier namespace
    # PHI redaction preserves identifier.system intact; direct authoritative signal.
    result = get_source_from_identifier_system(resource)
    if result:
        return _build_result(resource, result)

    # Priority 3: Determinative resource type — Tier A only
    result = get_source_from_resource_type(resource)
    if result:
        return _build_result(resource, result)

    # Priority 4: Observation category — Tier A only
    result = get_source_from_observation_category(resource)
    if result:
        return _build_result(resource, result)

    # Priority 5: Secondary signals — Tier A only (clinical_ehr vs administrative)
    result = get_source_from_secondary_signals(resource)
    if result:
        return _build_result(resource, result)

    # Priority 6: Topology cluster — Tier A only, low confidence
    result = get_source_from_topology_cluster(resource, cluster_registry)
    return _build_result(resource, result)


def _build_result(resource, inferred):
    """
    Build complete AuditEvent extension metadata including:
    - source-type (expanded vocabulary)
    - ecds-ssor (NCQA SSoR category)
    - source-inference-confidence
    """
    SOURCE_TYPE_TO_SSOR = {
        'clinical_ehr':                       'EHR/PHR',
        'clinical_phr':                       'EHR/PHR',
        'payer_exchange':                     'EHR/PHR',
        'administrative_claims':              'Administrative',
        'administrative_encounter':           'Administrative',
        'pharmacy_pbm':                       'Administrative',
        'pharmacy_specialty':                 'Administrative',
        'clinical_lab':                       'Clinical Registry/HIE',
        'clinical_hie':                       'Clinical Registry/HIE',
        'clinical_registry':                  'Clinical Registry/HIE',
        'clinical_immunization_registry':     'Clinical Registry/HIE',
        'case_management':                    'Case/Disease Mgmt',
        'disease_management':                 'Case/Disease Mgmt',
        'unknown':                             None,
    }

    source_type = inferred.get('source_type', 'unknown')
    feed_id = inferred.get('source_feed_id', 'unknown')
    sys_id = inferred.get('source_system_id', feed_id)

    return {
        'source_type':               source_type,
        'source_system_id':          sys_id,
        'source_feed_id':            feed_id,
        'ecds_ssor':                 SOURCE_TYPE_TO_SSOR.get(source_type),
        'confidence':                inferred.get('confidence', 'unknown'),
        'inference_basis':           inferred.get('inference_basis', 'none'),
    }
```

---

## Confidence Distribution as a Finding

The proportion of resources at each confidence tier is a direct provenance maturity metric requiring no additional testing.

```sql
-- Provenance coverage report — queries sof.audit_event_metadata (requires $materialize)
SELECT
  aem.confidence         AS confidence_tier,
  aem.source_type,
  aem.source_feed_id     AS feed_id,
  COUNT(*)               AS resource_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct
FROM sof.audit_event_metadata aem
GROUP BY 1, 2, 3
ORDER BY resource_count DESC;
```

### Maturity scoring

| Confidence distribution | Provenance maturity | Finding tier |
|---|---|---|
| >80% asserted | Governed — meta.source or Provenance implemented | No finding |
| 50-80% high + asserted | Adequate — resource structure signals strong | Tier 3 advisory |
| <50% high + asserted | Gap — inference-dependent | Tier 3 finding |
| >20% unknown | Material gap — MP2029 risk | Tier 3 HIGH severity |

---

## Undeclared Source Finding Template

```json
{
  "finding_id": "T3-PROV-001",
  "tier": 3,
  "domain": "Domain 3 — Data Lineage / Domain 6 — ECDS Readiness",
  "title": "Undeclared data sources in FHIR pipeline",
  "description": "N resources in the extract originate from source systems not declared in the client feed manifest. This indicates data flowing into the FHIR pipeline from systems outside the plan's documented inventory.",
  "evidence": "source-feed-id = undeclared-* in AuditEvent extension records",
  "severity": "HIGH",
  "my2029_risk": "HIGH — undeclared sources cannot be attributed in ECDS reporting",
  "remediation": "Audit the FHIR ingest pipeline to identify all upstream source systems. Update feed manifest and data governance inventory.",
  "remediation_owner": "Chief Data Officer / Data Governance function",
  "timeline": "Weeks — requires pipeline audit and governance process update"
}
```

---

## Cross-Reference

- **Framework:** DQAR Shared KB — `dqar-01-framework-summary.md` (Domain 3, Domain 6)
- **Application:** UC1 Assessment App — `dqar-06-uc1-app-technical-specification.md`
- **Use cases:** Applies to UC1, UC4 (CMS interoperability), UC5 (P2P exchange quality)
- **Partner guide:** `dqar-02-health-samurai-partner-guide.md` (Aidbox AuditEvent capabilities)
