import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from shared.engagement import load_engagement, get_fhir_headers

import requests

RESOURCE_TYPES = [
    "Patient", "Coverage", "Organization", "Practitioner",
    "PractitionerRole", "Location", "Condition", "Observation",
    "Encounter", "Procedure", "MedicationRequest", "MedicationDispense",
    "DiagnosticReport", "Immunization", "ServiceRequest",
    "ExplanationOfBenefit", "Provenance", "AuditEvent",
]

PAGE_SIZE = 1000


def fetch_all_resources(base_url: str, headers: dict, resource_type: str) -> list:
    resources = []
    url = f"{base_url}/fhir/{resource_type}"
    params = {"_count": PAGE_SIZE}

    while url:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        bundle = response.json()

        for entry in bundle.get("entry", []):
            resource = entry.get("resource")
            if resource:
                resources.append(resource)

        url = next(
            (link["url"] for link in bundle.get("link", []) if link["relation"] == "next"),
            None,
        )
        params = {}

    return resources


def write_ndjson(resources: list, dest: Path) -> int:
    with open(dest, "w") as f:
        for resource in resources:
            f.write(json.dumps(resource) + "\n")
    return len(resources)


def run_bulk_export(engagement_path: str, output_dir: str = "data/export") -> dict:
    engagement = load_engagement(engagement_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    print(f"Exporting from {engagement.base_url} ({engagement.server_type}) → {out}/\n")

    headers = get_fhir_headers(engagement)

    files = []
    totals = {}

    for resource_type in RESOURCE_TYPES:
        print(f"  Fetching {resource_type}...", end=" ", flush=True)
        resources = fetch_all_resources(engagement.base_url, headers, resource_type)
        dest = out / f"{resource_type}.ndjson"
        count = write_ndjson(resources, dest)
        totals[resource_type] = count
        files.append(str(dest))
        print(f"{count} records")

    summary = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "engagement": engagement.name,
        "server_type": engagement.server_type,
        "fhir_server": engagement.base_url,
        "method": "search-type",
        "resource_types": RESOURCE_TYPES,
        "totals": totals,
        "total_records": sum(totals.values()),
        "output_dir": str(out.resolve()),
        "files": files,
    }

    summary_path = out / "export-summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nExport complete. {summary['total_records']} total records across {len(files)} files.")
    print(f"Summary written to {summary_path}")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export FHIR resources to NDJSON")
    parser.add_argument("--engagement", required=True, help="Path to engagement config JSON")
    parser.add_argument("--output-dir", default="data/export")
    args = parser.parse_args()

    run_bulk_export(args.engagement, args.output_dir)
