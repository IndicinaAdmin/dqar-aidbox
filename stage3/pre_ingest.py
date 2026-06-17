"""
Pre-ingest enrichment pass for Stage 3.

Performs a single scan of the full tar.gz egress package before the resource
loop begins, building cross-file indices that the per-resource inference
algorithm cannot derive on its own:

  encounter_provider_index
    encounter_id → {system_id, feed_id, display}
    Built from Encounter.serviceProvider + Encounter.identifier.system.
    Allows Observations, Conditions, Procedures, and MedicationRequests
    to inherit organisational provenance from their linked Encounter even
    when they carry no identifier of their own.

  identifier_system_survey
    Counter of all identifier.system URIs across every resource type.
    Used to detect a dominant source system at the extract level, which
    becomes the auto_feed_manifest Priority 1 input.

  uuid_namespace_survey
    Counter of UUID prefix groups (first 3 dash-segments).  In a Synthea
    export each prefix corresponds to one patient.  For any bulk-FHIR
    server each unique prefix indicates one export cohort.

The IngestContext is passed to infer_source_metadata() and wired into
the priority chain as Priority 2.7 (encounter→provider resolution).

Coverage in client-redacted_pre.tar.gz:
  19386/19386 Observations resolvable via encounter→provider (100%)
  Similarly for Conditions, Procedures, MedicationRequests.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import tarfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field


@dataclass
class IngestContext:
    encounter_provider_index: dict[str, dict]   # encounter_id → provider metadata
    patient_provider_index: dict[str, dict]     # patient_id → dominant provider metadata
    identifier_system_survey: Counter            # system_uri → count across all resources
    uuid_namespace_survey: Counter               # uuid_prefix → count (proxy for patient count)
    dominant_identifier_system: str | None       # URI if one system accounts for ≥ 80% of id'd resources
    resource_counts: dict[str, int]              # resource_type → count
    patient_estimate: int                        # unique UUID namespace prefixes
    feed_manifest: dict | None = None            # parsed feed_manifest.json from the package


def _short_hash(value: str, prefix: str = "") -> str:
    return prefix + hashlib.sha256(value.encode()).hexdigest()[:12]


def _extract_uuid_prefix(resource_id: str) -> str | None:
    parts = resource_id.split("-")
    if len(parts) >= 3:
        return "-".join(parts[:3])
    return None


def build_ingest_context(package_path: str) -> IngestContext:
    """
    Single-pass scan of all NDJSON files in the egress package.

    Returns an IngestContext with cross-file indices.  Call this once
    before the Stage 3 resource loop; the result is passed into
    infer_source_metadata() as the `ingest_context` parameter.
    """
    encounter_provider_index: dict[str, dict] = {}
    identifier_system_survey: Counter = Counter()
    uuid_namespace_survey: Counter = Counter()
    resource_counts: dict[str, int] = {}
    identifier_bearing_resources = 0
    feed_manifest: dict | None = None

    # Raw patient→encounters accumulator used to build patient_provider_index below.
    # keyed by patient_id → list of provider metadata dicts (one per encounter)
    _patient_encounters: dict[str, list[dict]] = defaultdict(list)

    with tarfile.open(package_path, "r:gz") as tar:
        for member in tar.getmembers():
            f = tar.extractfile(member)
            if f is None:
                continue

            raw = f.read()

            # Feed manifest — JSON, not NDJSON
            if member.name == "feed_manifest.json":
                try:
                    feed_manifest = json.loads(raw)
                except json.JSONDecodeError:
                    pass
                continue

            if not (member.name.endswith(".ndjson") or
                    member.name.endswith(".ndjson.gz")):
                continue

            if member.name.endswith(".gz"):
                raw = gzip.decompress(raw)

            lines = raw.decode("utf-8").splitlines()

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    resource = json.loads(line)
                except json.JSONDecodeError:
                    continue

                resource_type = resource.get("resourceType", "Unknown")
                resource_counts[resource_type] = resource_counts.get(resource_type, 0) + 1

                # UUID namespace (patient-level grouping signal)
                rid = resource.get("id", "")
                prefix = _extract_uuid_prefix(rid)
                if prefix:
                    uuid_namespace_survey[prefix] += 1

                # identifier.system survey across all resource types
                for ident in resource.get("identifier", []):
                    sys = ident.get("system", "")
                    if sys:
                        identifier_system_survey[sys] += 1
                        identifier_bearing_resources += 1

                # Encounter-specific: build encounter→provider index
                if resource_type == "Encounter":
                    entry = _index_encounter(resource, encounter_provider_index)
                    if entry:
                        pat_ref = resource.get("subject", {}).get("reference", "")
                        pat_id = pat_ref.replace("urn:uuid:", "").split("/")[-1]
                        if pat_id:
                            _patient_encounters[pat_id].append(entry)

    dominant = _detect_dominant_system(identifier_system_survey,
                                       identifier_bearing_resources)

    patient_provider_index = _build_patient_provider_index(_patient_encounters)

    return IngestContext(
        encounter_provider_index=encounter_provider_index,
        patient_provider_index=patient_provider_index,
        identifier_system_survey=identifier_system_survey,
        uuid_namespace_survey=uuid_namespace_survey,
        dominant_identifier_system=dominant,
        resource_counts=resource_counts,
        patient_estimate=len(uuid_namespace_survey),
        feed_manifest=_normalise_feed_manifest(feed_manifest),
    )


_FRAMEWORK_TO_SOURCE_TYPE = {
    "hapi":       "clinical_ehr",
    "blaze":      "clinical_ehr",
    "azure-fhir": "clinical_ehr",
    "smile-cdr":  "clinical_ehr",
    "intersystems-iris": "clinical_ehr",
}


def _normalise_feed_manifest(manifest: dict | None) -> dict | None:
    """
    Normalise a feed_manifest dict produced by dqar-client-kit.

    Adds missing feed_id and maps server-framework source_system_type values
    (e.g. "hapi") to the DQAR source-type vocabulary (e.g. "clinical_ehr").
    The feed_id is derived from fhir_server_url when available, else from the
    source_system_type string — giving a stable, deduplicated identifier even
    when the client-kit didn't populate fhir_server_url yet.
    """
    if not manifest:
        return None

    for feed in manifest.get("feeds", []):
        # Resolve server-framework type names to vocabulary source types
        raw_type = feed.get("source_system_type", "")
        if raw_type in _FRAMEWORK_TO_SOURCE_TYPE:
            feed["source_system_type"] = _FRAMEWORK_TO_SOURCE_TYPE[raw_type]

        # Generate feed_id when missing
        if not feed.get("feed_id"):
            raw = feed.get("fhir_server_url") or feed.get("source_system_type") or "unknown"
            feed["feed_id"] = _short_hash(raw, "feed-")

    return manifest


def _index_encounter(encounter: dict,
                      index: dict[str, dict]) -> dict | None:
    """
    Extract provenance signals from one Encounter and add to the index.

    Captures both the source system (from identifier.system) and the
    organisational feed (from serviceProvider.display), keeping them
    separate so inference can assign EXT 2 and EXT 3 independently.

    Returns the index entry dict (for use in patient-level accumulation),
    or None if no useful signals were found.
    """
    eid = encounter.get("id", "")
    if not eid:
        return None

    # identifier.system → source system identity (EXT 2 candidate)
    id_system = None
    for ident in encounter.get("identifier", []):
        sys = ident.get("system", "")
        if sys:
            id_system = sys
            break

    # serviceProvider → organisational feed identity (EXT 3 candidate)
    sp = encounter.get("serviceProvider", {})
    sp_display = sp.get("display", "")
    sp_ref = sp.get("reference", "")

    # Use serviceProvider.reference as a stable fallback when display is absent.
    # Even a bare "Organization/132009851" ref gives a consistent feed_id across
    # all encounters that share the same provider.
    sp_key = sp_display or sp_ref
    if not sp_key and not id_system:
        return None

    entry = {
        "identifier_system": id_system,
        "provider_display":  sp_display or None,
        "provider_ref":      sp_ref or None,
        "system_id":         _short_hash(id_system, "enc-sys-") if id_system else None,
        "feed_id":           _short_hash(sp_key, "org-") if sp_key else None,
    }
    index[eid] = entry
    return entry


def _build_patient_provider_index(
    patient_encounters: dict[str, list[dict]]
) -> dict[str, dict]:
    """
    Build a patient_id → dominant provider entry for resources that carry
    a patient reference but no encounter reference (Device, AllergyIntolerance).

    A patient's dominant provider is returned only when one provider accounts
    for ≥ 80% of that patient's encounters, preventing false attribution for
    patients with genuinely multi-provider records.
    """
    result: dict[str, dict] = {}

    for patient_id, entries in patient_encounters.items():
        if not entries:
            continue

        # Count by feed_id (organisational provider) to find the dominant one
        feed_counter: Counter = Counter()
        feed_to_entry: dict[str, dict] = {}
        for e in entries:
            fid = e.get("feed_id") or e.get("system_id") or "unknown"
            feed_counter[fid] += 1
            feed_to_entry[fid] = e

        total = sum(feed_counter.values())
        top_fid, top_count = feed_counter.most_common(1)[0]

        if top_count / total >= 0.80:
            result[patient_id] = feed_to_entry[top_fid]

    return result


def _detect_dominant_system(survey: Counter,
                             total_with_id: int) -> str | None:
    """
    Return the identifier.system URI if one system accounts for ≥ 80% of
    all identifier-bearing resources across the extract.  Returns None if
    no single system dominates.
    """
    if total_with_id == 0 or not survey:
        return None
    top_uri, top_count = survey.most_common(1)[0]
    if top_count / total_with_id >= 0.80:
        return top_uri
    return None


def summarise(context: IngestContext) -> str:
    total = sum(context.resource_counts.values())
    lines = ["Pre-ingest scan summary:"]
    lines.append(f"  Total resources: {total}")
    lines.append(f"  By type: " + ", ".join(
        f"{rt}={n}" for rt, n in sorted(context.resource_counts.items())
    ))
    lines.append(f"  Patients (UUID namespaces): {context.patient_estimate}")
    lines.append(f"  Encounters indexed:          {len(context.encounter_provider_index)}")
    lines.append(f"  Patients with dominant provider (≥80%): {len(context.patient_provider_index)}")
    if context.dominant_identifier_system:
        lines.append(f"  Dominant identifier.system:  {context.dominant_identifier_system}")
    else:
        lines.append(f"  Dominant identifier.system:  none (mixed)")
    top5 = context.identifier_system_survey.most_common(5)
    if top5:
        lines.append("  Top identifier systems:")
        for uri, count in top5:
            lines.append(f"    {count:6d}x  {uri}")
    return "\n".join(lines)
