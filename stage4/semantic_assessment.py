"""
Stage 4 — SQL on FHIR semantic assessment.

SQL measure queries are loaded from dqar-contracts to ensure they stay in sync
with the ViewDefinitions loaded into Aidbox. Never hardcode measure SQL here.
"""

import importlib.resources as pkg
import requests


def _load_measure_sql(measure_name: str) -> str:
    """
    Load a parallel SQL reconstruction query from dqar-contracts.

    measure_name: filename without .sql extension, e.g. 'cbp_numerator'
    Returns the SQL string.
    Raises FileNotFoundError if the measure SQL does not exist in contracts.
    """
    sql_file = pkg.files("dqar_contracts") / "sql" / "measures" / f"{measure_name}.sql"
    return sql_file.read_text()


# Pre-loaded at module init — fail fast if contracts is missing expected SQL
CBP_NUMERATOR_SQL = _load_measure_sql("cbp_numerator")
CDC_HBA1C_NUMERATOR_SQL = _load_measure_sql("cdc_hba1c_numerator")


def run_cbp_numerator(aidbox_sql_url: str, headers: dict) -> dict:
    """
    Run CBP numerator reconstruction from dqar-contracts SQL.

    Returns dict with:
      - patients_in_numerator: set of patient IDs
      - results: list of rows with observation_id, ol_run_id, source_feed_id
      - population_count: int
    """
    sql = _load_measure_sql("cbp_numerator")
    response = requests.post(
        aidbox_sql_url,
        json=[sql],
        headers={**headers, "Content-Type": "application/json"}
    )
    response.raise_for_status()

    rows = response.json()
    # Aidbox /$sql returns a list of rows as lists
    # First row is column names, subsequent rows are data
    if not rows or len(rows) < 2:
        return {"patients_in_numerator": set(), "results": [], "population_count": 0}

    columns = rows[0]
    data_rows = rows[1:]
    results = [dict(zip(columns, row)) for row in data_rows]

    numerator_patients = {
        r["patient_id"] for r in results if r.get("cbp_numerator") is True
    }

    return {
        "patients_in_numerator": numerator_patients,
        "results": results,
        "population_count": len(results)
    }


def run_cdc_hba1c_numerator(aidbox_sql_url: str, headers: dict) -> dict:
    """
    Run CDC HbA1c numerator reconstruction from dqar-contracts SQL.

    Returns dict with:
      - patients_in_numerator: set of patient IDs
      - results: list of rows with observation_id, ol_run_id, source_feed_id
      - population_count: int
      - flagged_implausible: list of observation_ids with plausibility_flag=True
    """
    sql = _load_measure_sql("cdc_hba1c_numerator")
    response = requests.post(
        aidbox_sql_url,
        json=[sql],
        headers={**headers, "Content-Type": "application/json"}
    )
    response.raise_for_status()

    rows = response.json()
    if not rows or len(rows) < 2:
        return {
            "patients_in_numerator": set(),
            "results": [],
            "population_count": 0,
            "flagged_implausible": [],
        }

    columns = rows[0]
    data_rows = rows[1:]
    results = [dict(zip(columns, row)) for row in data_rows]

    numerator_patients = {r["patient_id"] for r in results}
    flagged = [r["observation_id"] for r in results if r.get("plausibility_flag") is True]

    return {
        "patients_in_numerator": numerator_patients,
        "results": results,
        "population_count": len(results),
        "flagged_implausible": flagged,
    }
