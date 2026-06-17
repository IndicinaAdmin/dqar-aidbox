"""
Materialize all ViewDefinitions in the init-bundle into sof.* views.

Run after loading the init-bundle into Aidbox. Creates a PostgreSQL VIEW
in the sof schema for every ViewDefinition. These views are what Stage 4
queries for dQM reports and lineage analysis.

Usage:
    python init_bundle/materialize.py --aidbox-url http://localhost:8080 --token <bearer>
    python init_bundle/materialize.py --aidbox-url http://localhost:8080 --client-id svc --client-secret secret
    python init_bundle/materialize.py  # reads AIDBOX_URL, AIDBOX_TOKEN from environment
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests


MATERIALIZE_ENDPOINT = "/fhir/ViewDefinition/$materialize"
MATERIALIZE_TYPE = "view"


def get_token(aidbox_url: str, client_id: str, client_secret: str) -> str:
    resp = requests.post(
        f"{aidbox_url}/auth/token",
        json={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def load_viewdef_names() -> list[str]:
    bundle_path = Path(__file__).parent / "init-bundle.json"
    bundle = json.loads(bundle_path.read_text())
    return [
        entry["resource"]["name"]
        for entry in bundle["entry"]
        if entry["resource"]["resourceType"] == "ViewDefinition"
    ]


def materialize_view(aidbox_url: str, headers: dict, name: str) -> bool:
    body = {
        "resourceType": "Parameters",
        "parameter": [
            {
                "name": "viewReference",
                "valueReference": {"reference": f"ViewDefinition/{name}"},
            },
            {
                "name": "type",
                "valueCode": MATERIALIZE_TYPE,
            },
        ],
    }
    resp = requests.post(
        f"{aidbox_url}{MATERIALIZE_ENDPOINT}",
        json=body,
        headers={**headers, "Content-Type": "application/json"},
        timeout=60,
    )

    if resp.status_code in (200, 201):
        result = resp.json()
        params = {p["name"]: p.get("valueString") for p in result.get("parameter", [])}
        print(f"  ✓ {name} → {params.get('viewName', 'sof.' + name)}")
        return True

    print(f"  ✗ {name} — HTTP {resp.status_code}: {resp.text[:200]}")
    return False


def main():
    parser = argparse.ArgumentParser(description="Materialize Aidbox sof.* views from init-bundle ViewDefinitions")
    parser.add_argument("--aidbox-url", default=os.environ.get("AIDBOX_URL", "http://localhost:8080"))
    parser.add_argument("--token", default=os.environ.get("AIDBOX_TOKEN"))
    parser.add_argument("--client-id", default=os.environ.get("AIDBOX_CLIENT_ID"))
    parser.add_argument("--client-secret", default=os.environ.get("AIDBOX_CLIENT_SECRET"))
    args = parser.parse_args()

    if args.token:
        token = args.token
    elif args.client_id and args.client_secret:
        token = get_token(args.aidbox_url, args.client_id, args.client_secret)
    else:
        print("ERROR: provide --token or both --client-id and --client-secret", file=sys.stderr)
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}
    names = load_viewdef_names()

    print(f"Materializing {len(names)} ViewDefinitions into sof.* views...")
    print(f"  Aidbox: {args.aidbox_url}")

    failed = []
    for name in names:
        if not materialize_view(args.aidbox_url, headers, name):
            failed.append(name)

    print()
    if failed:
        print(f"FAILED ({len(failed)}): {', '.join(failed)}", file=sys.stderr)
        sys.exit(1)

    print(f"All {len(names)} views materialized successfully.")


if __name__ == "__main__":
    main()
