"""
Stage 3 — Load egress package into Aidbox.

Accepts a tar.gz egress package from dqar-client-kit:
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
import uuid
from datetime import datetime, timezone

import requests

from stage3.inference import infer_source_metadata
from stage3.pre_ingest import build_ingest_context, summarise
from shared.lineage import emit_run_event

AIDBOX_URL = os.environ.get("AIDBOX_URL", "http://localhost:8080")
BUNDLE_BATCH_SIZE = int(os.environ.get("DQAR_BUNDLE_BATCH_SIZE", "200"))

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
            "who": {"display": f"dqar-aidbox/{pipeline_id}"},
            "requestor": True
        }],
        "source": {
            "observer": {"display": "dqar-aidbox stage3/load.py"}
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
    resp = requests.post(
        f"{AIDBOX_URL}/fhir",
        json=bundle,
        headers=post_headers,
        timeout=120,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Bundle POST failed HTTP {resp.status_code}: {resp.text[:500]}"
        )
    resource_count = len(bundle["entry"]) // 2
    return resource_count, 0


def _iter_ndjson(tar: tarfile.TarFile):
    for member in tar.getmembers():
        if not (member.name.endswith(".ndjson") or member.name.endswith(".ndjson.gz")):
            continue
        f = tar.extractfile(member)
        if f is None:
            continue
        raw = f.read()
        if member.name.endswith(".gz"):
            raw = gzip.decompress(raw)
        for line in raw.decode("utf-8").splitlines():
            line = line.strip()
            if line:
                yield json.loads(line)


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
        with tarfile.open(package_path, "r:gz") as tar:
            for resource in _iter_ndjson(tar):
                if resource.get("resourceType") == "Bundle":
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

    audit_event = _build_audit_event(resource, inference, pipeline_id, ol_run_id)
    batch.append((resource, audit_event))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Load DQAR egress package into Aidbox")
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
