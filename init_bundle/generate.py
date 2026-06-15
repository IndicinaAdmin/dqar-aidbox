"""
Generate the Aidbox Init Bundle from dqar-contracts artifacts.

Run at CI time before deployment. Writes init_bundle/init-bundle.json.
Never hand-edit init-bundle.json — always regenerate from contracts.

Usage:
    python init_bundle/generate.py
    python init_bundle/generate.py --output init_bundle/init-bundle.json
"""

import argparse
import importlib.resources as pkg
import json
from datetime import datetime, timezone
from pathlib import Path


def load_viewdefinitions() -> list:
    """Load all ViewDefinition JSON files from dqar-contracts."""
    vd_dir = pkg.files("dqar_contracts") / "viewdefinitions"
    viewdefs = []
    for entry in sorted(vd_dir.iterdir()):
        if not str(entry).endswith(".json"):
            continue
        vd = json.loads(entry.read_text())
        # Enforce: every ViewDefinition must have getResourceKey()
        has_rk = any(
            col.get("path") == "getResourceKey()"
            for select in vd.get("select", [])
            for col in select.get("column", [])
        )
        if not has_rk:
            raise ValueError(
                f"ViewDefinition '{vd.get('name')}' is missing getResourceKey() — "
                "lineage chain would break. Fix in dqar-contracts before generating Init Bundle."
            )
        viewdefs.append(vd)
    print(f"  Loaded {len(viewdefs)} ViewDefinitions from dqar-contracts")
    return viewdefs


def load_ext_definitions() -> dict:
    """Load AuditEvent extension definitions from dqar-contracts."""
    ext_file = pkg.files("dqar_contracts") / "audit_extensions" / "seven_extensions.json"
    return json.loads(ext_file.read_text())


def build_bundle(viewdefs: list, ext_defs: dict) -> dict:
    """
    Build the Aidbox Init Bundle.

    The bundle contains:
    - ViewDefinitions (from dqar-contracts, getResourceKey() enforced)
    - StructureDefinitions for the seven AuditEvent extensions (from dqar-contracts)

    AccessPolicies and Client resources are environment-specific and are loaded
    from environment variables or separate secret files at deploy time.
    They are NOT included in this generated bundle.
    """
    entries = []

    # ViewDefinitions
    for vd in viewdefs:
        entries.append({
            "resource": vd,
            "request": {
                "method": "PUT",
                "url": f"ViewDefinition/{vd.get('name', 'unknown')}"
            }
        })

    # AuditEvent extension StructureDefinitions
    for ext in ext_defs.get("extensions", []):
        sd = {
            "resourceType": "StructureDefinition",
            "id": f"indicina-{ext['id'].lower()}",
            "url": ext["url"],
            "name": f"DQAR{ext['id']}",
            "status": "active",
            "kind": "complex-type",
            "abstract": False,
            "type": "Extension",
            "baseDefinition": "http://hl7.org/fhir/StructureDefinition/Extension",
            "derivation": "constraint",
            "differential": {
                "element": [
                    {
                        "id": "Extension.value[x]",
                        "path": "Extension.value[x]",
                        "type": [{"code": ext["valueType"].replace("value", "")}]
                    }
                ]
            }
        }
        entries.append({
            "resource": sd,
            "request": {
                "method": "PUT",
                "url": f"StructureDefinition/indicina-{ext['id'].lower()}"
            }
        })

    return {
        "resourceType": "Bundle",
        "type": "transaction",
        "meta": {
            "tag": [{
                "system": "http://indicina.com/fhir/tags",
                "code": "init-bundle",
                "display": f"Generated {datetime.now(timezone.utc).isoformat()} from dqar-contracts"
            }]
        },
        "entry": entries
    }


def main():
    parser = argparse.ArgumentParser(description="Generate Aidbox Init Bundle from dqar-contracts")
    parser.add_argument("--output", default="init_bundle/init-bundle.json",
                        help="Output path for the generated bundle")
    args = parser.parse_args()

    print("Generating Init Bundle from dqar-contracts...")

    viewdefs = load_viewdefinitions()
    ext_defs = load_ext_definitions()
    bundle = build_bundle(viewdefs, ext_defs)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, indent=2))

    entry_count = len(bundle["entry"])
    print(f"  Generated {entry_count} bundle entries")
    print(f"  Written to {out}")
    print("Init Bundle generation complete.")


if __name__ == "__main__":
    main()
