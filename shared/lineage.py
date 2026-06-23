"""
OpenLineage event emission for CDAR ingest pipeline.

Events go directly to OpenMetadata (not via Marquez).
OpenMetadata natively consumes OpenLineage RunEvents.
"""

import json
import os
import importlib.resources as pkg
import requests
from datetime import datetime, timezone


OPENMETADATA_LINEAGE_URL = os.environ.get(
    "OPENMETADATA_LINEAGE_URL",
    "http://openmetadata:8585/api/v1/lineage/openlineage"
)


def emit_run_event(event_type: str, run_id: str, job_name: str,
                   inputs: list, outputs: list, facets: dict = None) -> bool:
    """
    Emit an OpenLineage RunEvent to OpenMetadata.

    event_type: 'START' | 'COMPLETE' | 'FAIL'
    run_id: UUID v4 — this is EXT 7 ol-run-id on all AuditEvents from this run
    job_name: human-readable job identifier
    inputs: list of OpenLineage Dataset dicts
    outputs: list of OpenLineage Dataset dicts
    facets: dict of OpenLineage facets (include CDAR run facet from contracts)

    Returns True if emission succeeded, False otherwise (non-fatal — lineage
    emission failure should not block ingest).
    """
    # Load the CDAR custom facet schema from contracts
    facet_schema = json.loads(
        (pkg.files("cdar_contracts") / "ol_facets" / "cdar_run_facet.json").read_text()
    )

    event = {
        "eventType": event_type,
        "eventTime": datetime.now(timezone.utc).isoformat(),
        "run": {
            "runId": run_id,
            "facets": {
                **(facets or {}),
            }
        },
        "job": {
            "namespace": "sonian.cdar",
            "name": job_name,
        },
        "inputs": inputs,
        "outputs": outputs,
        "producer": "https://github.com/indicina/cdar-aidbox-databricks-kit",
        "schemaURL": "https://openlineage.io/spec/1-0-5/OpenLineage.json"
    }

    if not OPENMETADATA_LINEAGE_URL:
        return True  # lineage disabled — non-fatal

    try:
        resp = requests.post(
            OPENMETADATA_LINEAGE_URL,
            json=event,
            timeout=5,
            headers={"Content-Type": "application/json"}
        )
        resp.raise_for_status()
        return True
    except Exception as exc:
        # Lineage emission is non-fatal — log and continue
        print(f"  [lineage] emit {event_type} failed (non-fatal): {exc}")
        return False
