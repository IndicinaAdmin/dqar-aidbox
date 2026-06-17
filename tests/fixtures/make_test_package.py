"""
Generate a minimal synthetic egress package for Stage 3 pipeline testing.

Produces tests/fixtures/test_package.tar.gz containing:
  - 2 Patients
  - 2 Encounters
  - 2 Conditions (hypertension, diabetes)
  - 2 BP Observations (CBP measure)
  - 2 HbA1c Observations (CDC measure)

Resources are US Core 6.1.0 conformant enough to exercise the full
Stage 3 → 4 → 5 pipeline. No PHI.
"""

import io
import json
import sys
import tarfile
from pathlib import Path

RESOURCES = {
    "Patient": [
        {
            "resourceType": "Patient",
            "id": "test-patient-001",
            "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]},
            "identifier": [{"system": "http://example.org/mrn", "value": "MRN001"}],
            "name": [{"use": "official", "family": "Synthea", "given": ["Alice"]}],
            "gender": "female",
            "birthDate": "1965-03-14",
            "active": True,
        },
        {
            "resourceType": "Patient",
            "id": "test-patient-002",
            "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]},
            "identifier": [{"system": "http://example.org/mrn", "value": "MRN002"}],
            "name": [{"use": "official", "family": "Synthea", "given": ["Bob"]}],
            "gender": "male",
            "birthDate": "1958-07-22",
            "active": True,
        },
    ],
    "Encounter": [
        {
            "resourceType": "Encounter",
            "id": "test-encounter-001",
            "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-encounter"]},
            "identifier": [{"system": "https://open.epic.com/FHIR/StructureDefinition/encounter-id", "value": "abc123hashed"}],
            "status": "finished",
            "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB"},
            "type": [{"coding": [{"system": "http://www.ama-assn.org/go/cpt", "code": "99213"}]}],
            "subject": {"reference": "Patient/test-patient-001"},
            "period": {"start": "2025-06-01T09:00:00Z", "end": "2025-06-01T09:30:00Z"},
        },
        {
            "resourceType": "Encounter",
            "id": "test-encounter-002",
            "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-encounter"]},
            "identifier": [{"system": "https://athenahealth.com/fhir/encounter-id", "value": "def456hashed"}],
            "status": "finished",
            "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB"},
            "type": [{"coding": [{"system": "http://www.ama-assn.org/go/cpt", "code": "99214"}]}],
            "subject": {"reference": "Patient/test-patient-002"},
            "period": {"start": "2025-08-15T14:00:00Z", "end": "2025-08-15T14:45:00Z"},
        },
    ],
    "Condition": [
        {
            "resourceType": "Condition",
            "id": "test-condition-001",
            "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition-problems-health-concerns"]},
            "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
            "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]},
            "code": {"coding": [{"system": "http://snomed.info/sct", "code": "38341003", "display": "Hypertensive disorder"}]},
            "subject": {"reference": "Patient/test-patient-001"},
            "encounter": {"reference": "Encounter/test-encounter-001"},
            "recordedDate": "2025-06-01",
        },
        {
            "resourceType": "Condition",
            "id": "test-condition-002",
            "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition-problems-health-concerns"]},
            "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
            "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]},
            "code": {"coding": [{"system": "http://snomed.info/sct", "code": "44054006", "display": "Diabetes mellitus type 2"}]},
            "subject": {"reference": "Patient/test-patient-002"},
            "encounter": {"reference": "Encounter/test-encounter-002"},
            "recordedDate": "2025-08-15",
        },
    ],
    "Observation": [
        {
            "resourceType": "Observation",
            "id": "test-obs-bp-001",
            "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-blood-pressure"]},
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}],
            "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel"}]},
            "subject": {"reference": "Patient/test-patient-001"},
            "encounter": {"reference": "Encounter/test-encounter-001"},
            "effectiveDateTime": "2025-06-01T09:15:00Z",
            "component": [
                {
                    "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}]},
                    "valueQuantity": {"value": 142, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
                },
                {
                    "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}]},
                    "valueQuantity": {"value": 88, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
                }
            ]
        },
        {
            "resourceType": "Observation",
            "id": "test-obs-bp-002",
            "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-blood-pressure"]},
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}],
            "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel"}]},
            "subject": {"reference": "Patient/test-patient-001"},
            "encounter": {"reference": "Encounter/test-encounter-001"},
            "effectiveDateTime": "2025-09-10T10:00:00Z",
            "component": [
                {
                    "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6"}]},
                    "valueQuantity": {"value": 128, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
                },
                {
                    "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4"}]},
                    "valueQuantity": {"value": 82, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
                }
            ]
        },
        {
            "resourceType": "Observation",
            "id": "test-obs-hba1c-001",
            "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-lab"]},
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory"}]}],
            "code": {"coding": [{"system": "http://loinc.org", "code": "4548-4", "display": "Hemoglobin A1c/Hemoglobin.total in Blood"}]},
            "subject": {"reference": "Patient/test-patient-002"},
            "encounter": {"reference": "Encounter/test-encounter-002"},
            "effectiveDateTime": "2025-08-15T11:00:00Z",
            "valueQuantity": {"value": 8.2, "unit": "%", "system": "http://unitsofmeasure.org", "code": "%"}
        },
        {
            "resourceType": "Observation",
            "id": "test-obs-hba1c-002",
            "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-lab"]},
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory"}]}],
            "code": {"coding": [{"system": "http://loinc.org", "code": "4548-4", "display": "Hemoglobin A1c/Hemoglobin.total in Blood"}]},
            "subject": {"reference": "Patient/test-patient-002"},
            "encounter": {"reference": "Encounter/test-encounter-002"},
            "effectiveDateTime": "2025-11-20T09:30:00Z",
            "valueQuantity": {"value": 7.6, "unit": "%", "system": "http://unitsofmeasure.org", "code": "%"}
        },
    ],
}


def build_tar_gz(output_path: Path):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for resource_type, resources in RESOURCES.items():
            ndjson = "\n".join(json.dumps(r) for r in resources) + "\n"
            data = ndjson.encode("utf-8")
            info = tarfile.TarInfo(name=f"{resource_type.lower()}.ndjson")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    output_path.write_bytes(buf.getvalue())
    total = sum(len(v) for v in RESOURCES.values())
    print(f"Written {output_path} ({total} resources across {len(RESOURCES)} types)")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "test_package.tar.gz"
    build_tar_gz(out)
