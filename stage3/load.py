"""
Stage 3 — Load egress package into Aidbox.

Accepts a tar.gz egress package from cdar-client-kit:
  - Decompresses NDJSON files per resource type
  - Runs source-type inference on each resource (EXT 1-5)
  - Builds batched transaction bundles (resource + AuditEvent pairs)
  - POSTs bundles to Aidbox with skip-reference-validation header
  - Emits OpenLineage RunEvents to OpenMetadata

EXT 6 (pipeline-id) and EXT 7 (ol-run-id) are set by the orchestrator
and passed in as arguments — they are NOT derived by inference.

Atomicity rule: resource and its AuditEvent are always in the same
transaction bundle entry pair. Never POST them separately.
"""

import gzip
import io
import json
import os
import tarfile
import time
import uuid
from datetime import datetime, timezone

import requests

from stage3.inference import infer_source_metadata
from stage3.pre_ingest import build_ingest_context, summarise
from shared.lineage import emit_run_event

AIDBOX_URL = os.environ.get("AIDBOX_URL", "http://localhost:8080")
# Default: single-pair bundles (1 resource + 1 AuditEvent per transaction).
# x-fhir-skip-reference-validation is not honoured for multi-resource transaction
# bundles on some Aidbox Edge sandboxes, so default 1 avoids cross-bundle reference
# failures. Production Aidbox (private network, skip-ref-validation working) can
# safely use CDAR_BUNDLE_BATCH_SIZE=200.
BUNDLE_BATCH_SIZE = int(os.environ.get("CDAR_BUNDLE_BATCH_SIZE", "1"))
_BUNDLE_MAX_RETRIES = int(os.environ.get("CDAR_BUNDLE_MAX_RETRIES", "3"))

EXT_SOURCE_TYPE       = "http://Sonian.io/fhir/ext/source-type"
EXT_SOURCE_SYSTEM_ID  = "http://Sonian.io/fhir/ext/source-system-id"
EXT_SOURCE_FEED_ID    = "http://Sonian.io/fhir/ext/source-feed-id"
EXT_CONFIDENCE        = "http://Sonian.io/fhir/ext/source-inference-confidence"
EXT_ECDS_SSOR         = "http://Sonian.io/fhir/ext/ecds-ssor"
EXT_PIPELINE_ID       = "http://Sonian.io/fhir/ext/ingest-pipeline-id"
EXT_OL_RUN_ID         = "http://Sonian.io/fhir/ext/ol-run-id"


def _build_audit_event(resource: dict, inference: dict,
                        pipeline_id: str, ol_run_id: str) -> dict:
    resource_type = resource.get("resourceType", "Unknown")
    resource_id = resource.get("id", "unknown")

    extensions = [
        {"url": EXT_SOURCE_TYPE,      "valueCode":   inference.get("source_type", "unknown")},
        {"url": EXT_SOURCE_SYSTEM_ID, "valueString": inference.get("source_system_id", "unknown")},
        {"url": EXT_SOURCE_FEED_ID,   "valueString": inference.get("source_feed_id", "unknown")},
        {"url": EXT_CONFIDENCE,       "valueCode":   inference.get("confidence", "unknown")},
        {"url": EXT_ECDS_SSOR,        "valueCode":   inference.get("ecds_ssor") or "unknown"},
        {"url": EXT_PIPELINE_ID,      "valueString": pipeline_id},
        {"url": EXT_OL_RUN_ID,        "valueString": ol_run_id},
    ]

    return {
        "resourceType": "AuditEvent",
        "recorded": datetime.now(timezone.utc).isoformat(),
        "type": {
            "system": "http://terminology.hl7.org/CodeSystem/audit-event-type",
            "code": "rest",
            "display": "RESTful Operation"
        },
        "action": "C",
        "outcome": "0",
        "agent": [{
            "type": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ParticipationType",
                    "code": "AUT"
                }]
            },
            "who": {"display": f"cdar-aidbox-databricks-kit/{pipeline_id}"},
            "requestor": True
        }],
        "source": {
            "observer": {"display": "cdar-aidbox-databricks-kit stage3/load.py"}
        },
        "entity": [{
            "what": {
                "reference": f"{resource_type}/{resource_id}",
                "type": resource_type
            },
            "role": {
                "system": "http://terminology.hl7.org/CodeSystem/object-role",
                "code": "4",
                "display": "Domain Resource"
            }
        }],
        "extension": extensions
    }


def _build_bundle(pairs: list[tuple[dict, dict]]) -> dict:
    entries = []
    for resource, audit_event in pairs:
        resource_type = resource["resourceType"]
        resource_id = resource.get("id")

        if resource_id:
            resource_request = {"method": "PUT", "url": f"{resource_type}/{resource_id}"}
        else:
            resource_request = {"method": "POST", "url": resource_type}

        entries.append({"resource": resource, "request": resource_request})
        entries.append({
            "resource": audit_event,
            "request": {"method": "POST", "url": "AuditEvent"}
        })

    return {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": entries
    }


def _post_bundle(bundle: dict, headers: dict) -> tuple[int, int]:
    post_headers = {
        **headers,
        "Content-Type": "application/fhir+json",
        "x-fhir-skip-reference-validation": "true",
    }
    last_exc = None
    for attempt in range(_BUNDLE_MAX_RETRIES):
        resp = requests.post(
            f"{AIDBOX_URL}/fhir",
            json=bundle,
            headers=post_headers,
            timeout=120,
        )
        if resp.status_code in (200, 201):
            resource_count = len(bundle["entry"]) // 2
            return resource_count, 0
        # Retry on transient 5xx (502 Bad Gateway, 503, 504)
        if resp.status_code >= 500:
            wait = 2 ** attempt
            print(f"  [load] transient {resp.status_code} on attempt {attempt+1}/{_BUNDLE_MAX_RETRIES}, retrying in {wait}s…")
            time.sleep(wait)
            last_exc = RuntimeError(
                f"Bundle POST failed HTTP {resp.status_code}: {resp.text[:500]}"
            )
            continue
        # 4xx — non-retryable validation failure
        raise RuntimeError(
            f"Bundle POST failed HTTP {resp.status_code}: {resp.text[:500]}"
        )
    raise last_exc


# Load order priority — lower number loads first, satisfying FK-style references.
# Resources with no clinical dependencies (Organizations, Patients) load before
# those that reference them (Encounters, Conditions, CarePlans, etc.).
_RESOURCE_TYPE_PRIORITY: dict[str, int] = {
    "Organization":          10,
    "Practitioner":          10,
    "PractitionerRole":      15,
    "Patient":               20,
    "RelatedPerson":         25,
    "Coverage":              30,
    "Encounter":             40,
    "Condition":             50,
    "Observation":           50,
    "Procedure":             50,
    "MedicationRequest":     50,
    "MedicationStatement":   50,
    "MedicationAdministration": 50,
    "AllergyIntolerance":    50,
    "Immunization":          50,
    "DiagnosticReport":      55,
    "DocumentReference":     55,
    "Task":                  60,
    "Appointment":           60,
    "CareTeam":              70,
    "CarePlan":              80,
    "ExplanationOfBenefit":  80,
}

_DEFAULT_PRIORITY = 50


def _member_priority(member: tarfile.TarInfo) -> int:
    """Return load order priority for a tar member by resource type in filename."""
    name = member.name.rstrip(".gz").rstrip(".ndjson")
    # Handle paths like "dir/ResourceType.ndjson.gz"
    base = name.split("/")[-1]
    return _RESOURCE_TYPE_PRIORITY.get(base, _DEFAULT_PRIORITY)


def _strip_empty_collections(obj):
    """Recursively remove empty arrays and None values.

    FHIR R4 forbids empty arrays — Aidbox rejects them with 'empty-value'.
    """
    if isinstance(obj, dict):
        return {k: _strip_empty_collections(v) for k, v in obj.items()
                if v is not None and v != [] and v != {}}
    if isinstance(obj, list):
        cleaned = [_strip_empty_collections(i) for i in obj]
        return [i for i in cleaned if i is not None and i != [] and i != {}]
    return obj


def _iter_ndjson(tar: tarfile.TarFile):
    members = [m for m in tar.getmembers()
               if m.name.endswith(".ndjson") or m.name.endswith(".ndjson.gz")]
    members.sort(key=_member_priority)

    for member in members:
        f = tar.extractfile(member)
        if f is None:
            continue
        raw = f.read()
        if member.name.endswith(".gz"):
            raw = gzip.decompress(raw)
        for line in raw.decode("utf-8").splitlines():
            line = line.strip()
            if line:
                resource = json.loads(line)
                resource["_source_file"] = member.name  # for feed manifest matching
                yield resource


def load_egress_package(
    package_path: str,
    pipeline_id: str,
    ol_run_id: str,
    headers: dict,
    feed_manifest: dict = None,
    cluster_registry: dict = None,
) -> dict:
    """
    Load a tar.gz egress package into Aidbox.

    package_path: path to the tar.gz file
    pipeline_id: EXT 6 — set by orchestrator
    ol_run_id: EXT 7 — set by orchestrator (OpenLineage run UUID)
    headers: Aidbox auth headers (Authorization: Bearer ...)
    feed_manifest: optional manifest from the egress package for inference
    cluster_registry: optional cluster registry for inference

    Returns a summary dict with counts and any failed resource IDs.
    """
    print("[load] pre-ingest scan …")
    ingest_context = build_ingest_context(package_path)
    print(summarise(ingest_context))
    # Use the feed manifest from the package if none was passed explicitly
    if feed_manifest is None and ingest_context.feed_manifest:
        feed_manifest = ingest_context.feed_manifest
        print(f"[load] using feed_manifest from package ({len(feed_manifest.get('feeds', []))} feed(s))")

    emit_run_event(
        event_type="START",
        run_id=ol_run_id,
        job_name="stage3.load",
        inputs=[{"namespace": "s3", "name": package_path}],
        outputs=[{"namespace": "aidbox", "name": "fhir"}],
        facets={"pipeline_id": {"_producer": pipeline_id, "value": pipeline_id}},
    )

    total_loaded = 0
    total_failed = 0
    failed_ids = []
    batch: list[tuple[dict, dict]] = []

    def flush_batch():
        nonlocal total_loaded, total_failed
        if not batch:
            return
        try:
            loaded, _ = _post_bundle(_build_bundle(batch), headers)
            total_loaded += loaded
        except RuntimeError as exc:
            print(f"  [load] batch failed: {exc}")
            total_failed += len(batch)
            failed_ids.extend(
                r.get("id", "no-id") for r, _ in batch
            )
        batch.clear()

    try:
        current_priority = None
        with tarfile.open(package_path, "r:gz") as tar:
            for resource in _iter_ndjson(tar):
                resource_type = resource.get("resourceType")
                resource_priority = _RESOURCE_TYPE_PRIORITY.get(
                    resource_type, _DEFAULT_PRIORITY
                )

                # Flush when crossing a priority boundary so lower-priority
                # resources (e.g. Patients) are committed before higher-priority
                # ones (e.g. Encounters) reference them.
                if current_priority is not None and resource_priority != current_priority:
                    flush_batch()
                current_priority = resource_priority

                if resource_type == "Bundle":
                    for entry in resource.get("entry", []):
                        _process_resource(
                            entry.get("resource", {}),
                            batch, pipeline_id, ol_run_id,
                            feed_manifest, cluster_registry, ingest_context,
                        )
                        if len(batch) >= BUNDLE_BATCH_SIZE:
                            flush_batch()
                else:
                    _process_resource(
                        resource, batch, pipeline_id, ol_run_id,
                        feed_manifest, cluster_registry, ingest_context,
                    )
                    if len(batch) >= BUNDLE_BATCH_SIZE:
                        flush_batch()

        flush_batch()

    except Exception as exc:
        emit_run_event(
            event_type="FAIL",
            run_id=ol_run_id,
            job_name="stage3.load",
            inputs=[{"namespace": "s3", "name": package_path}],
            outputs=[{"namespace": "aidbox", "name": "fhir"}],
        )
        raise

    emit_run_event(
        event_type="COMPLETE",
        run_id=ol_run_id,
        job_name="stage3.load",
        inputs=[{"namespace": "s3", "name": package_path}],
        outputs=[{"namespace": "aidbox", "name": "fhir"}],
        facets={"resourcesLoaded": {"_producer": pipeline_id, "value": total_loaded}},
    )

    return {
        "total_loaded": total_loaded,
        "total_failed": total_failed,
        "failed_ids": failed_ids,
        "ol_run_id": ol_run_id,
        "pipeline_id": pipeline_id,
    }


def _process_resource(resource: dict, batch: list,
                       pipeline_id: str, ol_run_id: str,
                       feed_manifest: dict, cluster_registry: dict,
                       ingest_context=None):
    resource_type = resource.get("resourceType")
    if not resource_type or resource_type == "AuditEvent":
        return

    inference = infer_source_metadata(
        resource,
        feed_manifest=feed_manifest,
        cluster_registry=cluster_registry,
        ingest_context=ingest_context,
    )

    if inference.get("source_type") == "unknown":
        print(
            f"  [load] unknown source-type for {resource_type}/{resource.get('id', '?')} "
            f"(basis: {inference.get('inference_basis', '?')}) — will surface as finding"
        )

    # Strip pipeline-internal annotation before sending to Aidbox
    resource.pop("_source_file", None)

    # FHIR R4 forbids empty arrays — strip before validation
    resource = _strip_empty_collections(resource)

    audit_event = _build_audit_event(resource, inference, pipeline_id, ol_run_id)
    batch.append((resource, audit_event))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Load CDAR egress package into Aidbox")
    parser.add_argument("package", help="Path to egress tar.gz")
    parser.add_argument("--pipeline-id", default=f"pipeline-{uuid.uuid4()}")
    parser.add_argument("--ol-run-id", default=str(uuid.uuid4()))
    parser.add_argument("--token", default=os.environ.get("AIDBOX_TOKEN"))
    args = parser.parse_args()

    if not args.token:
        raise SystemExit("ERROR: --token or AIDBOX_TOKEN required")

    result = load_egress_package(
        package_path=args.package,
        pipeline_id=args.pipeline_id,
        ol_run_id=args.ol_run_id,
        headers={"Authorization": f"Bearer {args.token}"},
    )
    print(json.dumps(result, indent=2))
