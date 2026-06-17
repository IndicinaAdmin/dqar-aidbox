"""
Source-type inference algorithm.
Full specification: specs/dqar-05-source-inference-algorithm.md

Priority chain (first match wins):
  0  Provenance lookup    — asserted; requires API callback; see amendment spec
  1  Feed manifest        — asserted
  2  meta.source URI      — asserted; resolves all Tier A + Tier B types
  2.5 identifier.system   — asserted; Encounter/Patient/Org identifier URIs
  3  Determinative type   — high; ExplanationOfBenefit, MedicationDispense, etc.
  4  Observation.category — high; laboratory → clinical_lab, vital-signs → clinical_ehr
  5  Secondary signals    — medium; coding systems + field presence scoring
  6  Topology cluster     — low; structural fingerprint grouping

EXT 6 (ingest-pipeline-id) and EXT 7 (ol-run-id) are set by the orchestrator.
This module only produces EXT 1–5.
"""

from __future__ import annotations

import hashlib
import json

SOURCE_TYPE_TO_SSOR: dict[str, str | None] = {
    "clinical_ehr":                   "EHR/PHR",
    "clinical_phr":                   "EHR/PHR",
    "payer_exchange":                 "EHR/PHR",
    "administrative_claims":          "Administrative",
    "administrative_encounter":       "Administrative",
    "pharmacy_pbm":                   "Administrative",
    "pharmacy_specialty":             "Administrative",
    "clinical_lab":                   "Clinical Registry/HIE",
    "clinical_hie":                   "Clinical Registry/HIE",
    "clinical_registry":              "Clinical Registry/HIE",
    "clinical_immunization_registry": "Clinical Registry/HIE",
    "case_management":                "Case/Disease Mgmt",
    "disease_management":             "Case/Disease Mgmt",
    "unknown":                        None,
}

# URIs treated as non-informative — present in synthetic/test data but carry no
# source-system meaning. Filtered out before identifier.system pattern matching.
_NON_INFORMATIVE_ID_SYSTEMS = {
    "http://example.org/mrn",
    "http://example.org/",
    "http://example.com/",
    "http://hl7.org/fhir/sid/us-ssn",
    "urn:ietf:rfc:3986",
    "http://terminology.hl7.org/",
    "https://github.com/synthetichealth/synthea",
}

DETERMINATIVE_RESOURCE_TYPES: dict[str, tuple[str, str]] = {
    "ExplanationOfBenefit": ("administrative_claims",          "high"),
    "Claim":                ("administrative_claims",          "high"),
    "ClaimResponse":        ("administrative_claims",          "high"),
    "Coverage":             ("administrative_claims",          "high"),
    "MedicationDispense":   ("pharmacy_pbm",                   "high"),
    "Immunization":         ("clinical_immunization_registry", "high"),
}

OBSERVATION_CATEGORY_MAP: dict[str, tuple[str, str]] = {
    "laboratory":     ("clinical_lab", "high"),
    "vital-signs":    ("clinical_ehr", "high"),
    "clinical-test":  ("clinical_ehr", "high"),
    "exam":           ("clinical_ehr", "high"),
    "survey":         ("clinical_ehr", "high"),
    "social-history": ("clinical_ehr", "high"),
    "activity":       ("clinical_ehr", "high"),
    "imaging":        ("clinical_ehr", "high"),
    "procedure":      ("clinical_ehr", "high"),
    "therapy":        ("clinical_ehr", "high"),
}


def _uri_to_source_type(uri: str) -> str | None:
    """
    Map a URI (from meta.source or identifier.system) to a source-type code.
    Returns None if the URI doesn't match any known pattern.
    Applied identically in Priority 2 and Priority 2.5.
    """
    u = uri.lower()

    if any(k in u for k in ["phr", "myhealth", "patient-app", "personal-health"]):
        return "clinical_phr"
    if any(k in u for k in ["commonwell", "carequality", "rhio",
                              "health-information-exchange"]):
        return "clinical_hie"
    if any(k in u for k in ["registry", "clinical-registry",
                              "oncology-registry", "cardiac-registry"]):
        return "clinical_registry"
    if any(k in u for k in ["case-management", "case_management",
                              "care-management", "casemanagement"]):
        return "case_management"
    if any(k in u for k in ["disease-management", "disease_management",
                              "dm-program", "chronic-care"]):
        return "disease_management"
    if any(k in u for k in ["specialty-pharmacy", "specialty_pharmacy",
                              "biologics", "accredo", "cvs-specialty",
                              "walgreens-specialty"]):
        return "pharmacy_specialty"
    if any(k in u for k in ["pharmacy", "pbm", "rxclaim", "medco",
                              "express-scripts", "caremark", "optumrx"]):
        return "pharmacy_pbm"
    if any(k in u for k in ["quest", "labcorp", "pathology", "lims",
                              "laboratory"]):
        return "clinical_lab"
    if any(k in u for k in ["p2p", "pdex", "payer-exchange", "payer_exchange"]):
        return "payer_exchange"
    if any(k in u for k in ["claims", "adjudic", "eob", "billing"]):
        return "administrative_claims"
    if any(k in u for k in ["epic", "cerner", "meditech", "allscripts",
                              "athena", "ehr", "emr"]):
        return "clinical_ehr"
    # IIS / immunization registry URIs
    if any(k in u for k in ["iis", "immunization-registry",
                              "vxu", "immunizationregistry"]):
        return "clinical_immunization_registry"
    return None


def _short_hash(value: str, prefix: str = "") -> str:
    return prefix + hashlib.sha256(value.encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Priority 0 — Provenance lookup
# ---------------------------------------------------------------------------

def get_source_from_provenance(resource: dict, provenance_lookup) -> dict | None:
    """
    Priority 0: resolve source from an existing FHIR Provenance resource.

    provenance_lookup: callable(resource_type, resource_id) → Provenance dict | None
    If no lookup callback provided, or if no Provenance found, returns None.

    Spec: specs/dqar-05-amendment-priority-0-provenance.md (to be authored).
    """
    if provenance_lookup is None:
        return None
    resource_type = resource.get("resourceType", "")
    resource_id = resource.get("id", "")
    if not resource_id:
        return None
    provenance = provenance_lookup(resource_type, resource_id)
    if not provenance:
        return None
    # Extract agent.who — the system that created the resource
    for agent in provenance.get("agent", []):
        who = agent.get("who", {})
        sys_ref = who.get("identifier", {}).get("system", "")
        sys_display = who.get("display", "")
        uri = sys_ref or sys_display
        if uri:
            source_type = _uri_to_source_type(uri) or "clinical_ehr"
            return {
                "source_type": source_type,
                "source_system_id": _short_hash(uri, "prov-"),
                "source_feed_id": _short_hash(uri, "prov-"),
                "confidence": "asserted",
                "inference_basis": f"Provenance.agent.who={uri}",
            }
    return None


# ---------------------------------------------------------------------------
# Priority 1 — Feed manifest
# ---------------------------------------------------------------------------

def get_source_from_manifest(resource: dict, feed_manifest: dict | None) -> dict | None:
    filename = resource.get("_source_file")
    if not feed_manifest or not filename:
        return None

    for feed in feed_manifest.get("feeds", []):
        if filename in feed.get("files", []):
            return {
                "source_type":   feed["source_system_type"],
                "source_feed_id": feed["feed_id"],
                "source_system_id": feed.get("source_system_id", feed["feed_id"]),
                "confidence":    "asserted",
                "inference_basis": f"feed-manifest:{feed['feed_id']}",
            }

    return {
        "source_type":    "unknown",
        "source_feed_id": f"undeclared-{filename}",
        "source_system_id": f"undeclared-{filename}",
        "confidence":     "unknown",
        "inference_basis": f"manifest-miss:{filename}",
    }


# ---------------------------------------------------------------------------
# Priority 2 — meta.source URI
# ---------------------------------------------------------------------------

def get_source_from_meta(resource: dict) -> dict | None:
    meta_source = resource.get("meta", {}).get("source")
    if not meta_source:
        return None

    source_type = _uri_to_source_type(meta_source) or "clinical_ehr"
    sys_id = _short_hash(meta_source, "meta-")

    return {
        "source_type":    source_type,
        "source_system_id": sys_id,
        "source_feed_id": sys_id,
        "confidence":     "asserted",
        "inference_basis": f"meta.source={meta_source}",
    }


# ---------------------------------------------------------------------------
# Priority 2.5 — identifier.system URI
# ---------------------------------------------------------------------------

def get_source_from_identifier_system(resource: dict) -> dict | None:
    """
    Priority 2.5: derive source-system-id (and source-type where pattern matches)
    from FHIR identifier.system URIs.

    identifier.system URIs survive PHI redaction intact — only identifier.value
    is hashed, not identifier.system. This makes them a direct, authoritative
    signal for which source system produced the resource.

    Returns asserted confidence when a URI pattern is recognized.
    Returns medium confidence when a URI is present but the pattern is unknown
    (we know the system URI but cannot classify the type — still provides
    source_system_id, which is more useful than a topology hash).

    Tier B types (clinical_phr, clinical_hie, case_management, disease_management)
    are resolvable here because identifier.system URIs like
    "https://commonwell.org/patient-id" or "https://myhealth.org/record-id"
    are explicit declarations by the source system.
    """
    identifiers = resource.get("identifier", [])
    if not identifiers:
        return None

    for ident in identifiers:
        system = ident.get("system", "")
        if not system:
            continue
        # Skip non-informative systems (synthetic data, example placeholders)
        if any(system.startswith(skip) for skip in _NON_INFORMATIVE_ID_SYSTEMS):
            continue
        if system in _NON_INFORMATIVE_ID_SYSTEMS:
            continue

        source_type = _uri_to_source_type(system)
        sys_id = _short_hash(system, "id-sys-")

        if source_type:
            return {
                "source_type":    source_type,
                "source_system_id": sys_id,
                "source_feed_id": sys_id,
                "confidence":     "asserted",
                "inference_basis": f"identifier.system={system}",
            }
        else:
            # URI present and informative but pattern not recognized.
            # Provide source_system_id (eliminates unknown) but downgrade to medium.
            return {
                "source_type":    "clinical_ehr",
                "source_system_id": sys_id,
                "source_feed_id": sys_id,
                "confidence":     "medium",
                "inference_basis": f"identifier.system={system} (unrecognized-pattern → clinical_ehr default)",
            }

    return None


# ---------------------------------------------------------------------------
# Priority 3 — Determinative resource type
# ---------------------------------------------------------------------------

def get_source_from_resource_type(resource: dict) -> dict | None:
    rt = resource.get("resourceType")
    if rt not in DETERMINATIVE_RESOURCE_TYPES:
        return None

    source_type, confidence = DETERMINATIVE_RESOURCE_TYPES[rt]

    if rt == "MedicationDispense":
        id_systems = [
            i.get("system", "").lower()
            for i in resource.get("identifier", [])
        ]
        specialty_signals = ["specialty", "biologics", "accredo", "cvs-specialty",
                             "walgreens-specialty", "coram", "bioscrip"]
        if any(sig in sys for sys in id_systems for sig in specialty_signals):
            source_type = "pharmacy_specialty"

    if rt == "Immunization":
        if resource.get("primarySource") is not False:
            source_type = "clinical_ehr"

    return {
        "source_type":    source_type,
        "confidence":     confidence,
        "inference_basis": f"resourceType={rt}",
    }


# ---------------------------------------------------------------------------
# Priority 4 — Observation.category
# ---------------------------------------------------------------------------

def get_source_from_observation_category(resource: dict) -> dict | None:
    if resource.get("resourceType") != "Observation":
        return None

    for cat in resource.get("category", []):
        for coding in cat.get("coding", []):
            code = coding.get("code", "").lower()
            if code in OBSERVATION_CATEGORY_MAP:
                source_type, confidence = OBSERVATION_CATEGORY_MAP[code]
                return {
                    "source_type":    source_type,
                    "confidence":     confidence,
                    "inference_basis": f"Observation.category={code}",
                }
    return None


# ---------------------------------------------------------------------------
# Priority 5 — Secondary signals (Condition, Encounter, Procedure)
# ---------------------------------------------------------------------------

def get_source_from_secondary_signals(resource: dict) -> dict | None:
    rt = resource.get("resourceType")
    ehr_score = 0
    admin_score = 0
    signals: list[str] = []

    if rt == "Condition":
        codes = resource.get("code", {}).get("coding", [])
        systems = [c.get("system", "") for c in codes]
        has_snomed = any("snomed" in s.lower() for s in systems)
        has_icd10  = any("icd-10" in s.lower() or "icd10" in s.lower() for s in systems)

        if has_snomed and not has_icd10:
            ehr_score += 2; signals.append("SNOMED-only")
        elif has_icd10 and not has_snomed:
            admin_score += 2; signals.append("ICD10-only")
        elif has_snomed and has_icd10:
            ehr_score += 1; signals.append("dual-coded")

        vs = (resource.get("verificationStatus") or {}).get("coding", [{}])[0].get("code", "")
        if vs == "confirmed":
            ehr_score += 2; signals.append("verificationStatus=confirmed")
        elif not vs:
            admin_score += 1; signals.append("verificationStatus=absent")

        if resource.get("onsetDateTime") or resource.get("onsetPeriod"):
            ehr_score += 1; signals.append("onset-date-present")
        if resource.get("recorder"):
            ehr_score += 2; signals.append("recorder-present")

    elif rt == "Encounter":
        for et in resource.get("type", []):
            for coding in et.get("coding", []):
                system = coding.get("system", "").lower()
                if "cpt" in system or "hcpcs" in system:
                    admin_score += 2; signals.append("CPT-type-code"); break
                elif "snomed" in system:
                    ehr_score += 2; signals.append("SNOMED-type-code"); break

        participants = resource.get("participant", [])
        if len(participants) > 1:
            ehr_score += 2; signals.append(f"{len(participants)}-participants")
        elif len(participants) == 0:
            admin_score += 1; signals.append("no-participants")

        if resource.get("location"):
            ehr_score += 1; signals.append("location-present")

    elif rt == "Procedure":
        codes = resource.get("code", {}).get("coding", [])
        systems = [c.get("system", "") for c in codes]
        has_snomed = any("snomed" in s.lower() for s in systems)
        has_cpt    = any("cpt" in s.lower() or "hcpcs" in s.lower() for s in systems)

        if has_snomed:
            ehr_score += 2; signals.append("SNOMED-procedure")
        if has_cpt and not has_snomed:
            admin_score += 1; signals.append("CPT-only")
        if resource.get("performer"):
            ehr_score += 2; signals.append("performer-present")

    else:
        return None

    if ehr_score == 0 and admin_score == 0:
        return None

    basis = ", ".join(signals)
    if ehr_score > admin_score:
        return {
            "source_type":    "clinical_ehr",
            "confidence":     "medium",
            "inference_basis": basis,
            "ehr_score":      ehr_score,
            "admin_score":    admin_score,
        }
    elif admin_score > ehr_score:
        source_type = "administrative_encounter" if rt == "Encounter" else "administrative_claims"
        return {
            "source_type":    source_type,
            "confidence":     "medium",
            "inference_basis": basis,
            "ehr_score":      ehr_score,
            "admin_score":    admin_score,
        }
    else:
        return {
            "source_type":    "clinical_ehr",
            "confidence":     "low",
            "inference_basis": f"tied-score: {basis}",
            "ehr_score":      ehr_score,
            "admin_score":    admin_score,
        }


# ---------------------------------------------------------------------------
# Priority 6 — Topology cluster
# ---------------------------------------------------------------------------

def compute_topology_fingerprint(resource: dict) -> str:
    rt = resource.get("resourceType", "")

    code_systems: set[str] = set()
    for coding in resource.get("code", {}).get("coding", []):
        if coding.get("system"):
            code_systems.add(coding["system"])

    id_systems: set[str] = set()
    for identifier in resource.get("identifier", []):
        if identifier.get("system"):
            id_systems.add(identifier["system"])

    fingerprint_data = {
        "resource_type":      rt,
        "code_systems":       sorted(code_systems),
        "identifier_systems": sorted(id_systems),
        "field_presence": {
            "has_meta_source":         bool(resource.get("meta", {}).get("source")),
            "has_recorder":            bool(resource.get("recorder")),
            "has_performer":           bool(resource.get("performer")),
            "has_participants":        bool(resource.get("participant")),
            "has_location":            bool(resource.get("location")),
            "has_onset":               bool(resource.get("onsetDateTime") or resource.get("onsetPeriod")),
            "has_verification_status": bool(resource.get("verificationStatus")),
            "category_codes": sorted([
                c.get("code", "")
                for cat in resource.get("category", [])
                for c in cat.get("coding", [])
            ]),
        },
    }

    raw = json.dumps(fingerprint_data, sort_keys=True)
    return "topology-" + hashlib.sha256(raw.encode()).hexdigest()[:8]


def get_source_from_topology_cluster(resource: dict,
                                     cluster_registry: dict) -> dict:
    fingerprint = compute_topology_fingerprint(resource)

    if fingerprint in cluster_registry:
        cluster = cluster_registry[fingerprint]
        cluster["count"] += 1
        return {
            "source_type":    cluster["majority_source_type"],
            "source_feed_id": fingerprint,
            "source_system_id": fingerprint,
            "confidence":     "low",
            "inference_basis": f"topology-cluster={fingerprint} (n={cluster['count']})",
        }

    cluster_registry[fingerprint] = {
        "fingerprint":          fingerprint,
        "resource_type":        resource.get("resourceType"),
        "count":                1,
        "majority_source_type": "unknown",
    }
    return {
        "source_type":    "unknown",
        "source_feed_id": fingerprint,
        "source_system_id": fingerprint,
        "confidence":     "low",
        "inference_basis": f"new-topology-cluster={fingerprint}",
    }


# ---------------------------------------------------------------------------
# Master function
# ---------------------------------------------------------------------------

def _build_result(inferred: dict) -> dict:
    source_type = inferred.get("source_type", "unknown")
    feed_id     = inferred.get("source_feed_id", "unknown")
    sys_id      = inferred.get("source_system_id", feed_id)

    return {
        "source_type":      source_type,
        "source_system_id": sys_id,
        "source_feed_id":   feed_id,
        "ecds_ssor":        SOURCE_TYPE_TO_SSOR.get(source_type),
        "confidence":       inferred.get("confidence", "unknown"),
        "inference_basis":  inferred.get("inference_basis", "none"),
    }


def infer_source_metadata(
    resource: dict,
    feed_manifest: dict | None = None,
    cluster_registry: dict | None = None,
    provenance_lookup=None,
) -> dict:
    """
    Run inference priorities 0–6 in order. Return first successful result.

    Always returns a dict with:
      source_type, source_system_id, source_feed_id, ecds_ssor,
      confidence, inference_basis

    EXT 6 (ingest-pipeline-id) and EXT 7 (ol-run-id) are set by the
    orchestrator and are NOT part of this return dict.

    Args:
        resource: FHIR resource dict (with optional _source_file annotation)
        feed_manifest: optional manifest from the egress package
        cluster_registry: mutable dict shared across calls for topology clustering;
                          pass {} and reuse across all resources in a batch
        provenance_lookup: optional callable(resource_type, id) → Provenance | None
    """
    if cluster_registry is None:
        cluster_registry = {}

    # Priority 0 — Provenance (requires API callback; skipped if not provided)
    result = get_source_from_provenance(resource, provenance_lookup)
    if result:
        return _build_result(result)

    # Priority 1 — Feed manifest
    result = get_source_from_manifest(resource, feed_manifest)
    if result and result.get("confidence") != "unknown":
        return _build_result(result)

    # Priority 2 — meta.source URI
    result = get_source_from_meta(resource)
    if result:
        return _build_result(result)

    # Priority 2.5 — identifier.system URI
    # identifier.system URIs survive PHI redaction; direct authoritative signal.
    result = get_source_from_identifier_system(resource)
    if result:
        return _build_result(result)

    # Priority 3 — Determinative resource type
    result = get_source_from_resource_type(resource)
    if result:
        return _build_result(result)

    # Priority 4 — Observation.category
    result = get_source_from_observation_category(resource)
    if result:
        return _build_result(result)

    # Priority 5 — Secondary signals (Condition, Encounter, Procedure)
    result = get_source_from_secondary_signals(resource)
    if result:
        return _build_result(result)

    # Priority 6 — Topology cluster (always returns something)
    result = get_source_from_topology_cluster(resource, cluster_registry)
    return _build_result(result)
