"""
Stage 4 — SQL on FHIR semantic assessment.

Queries sof.* materialized views rather than raw JSONB tables. This means:
  - All measure SQL runs against flat, indexed columns (not JSONB extraction)
  - Lineage tracing is a JOIN on sof.audit_event_metadata (not LATERAL unnest)
  - The same SQL runs in any PostgreSQL-compatible analytics tool

ViewDefinitions must be materialized before this stage runs.
Call init_bundle/materialize.py after loading the init-bundle.

Parallel SQL reconstruction queries are still loaded from cdar-contracts
to stay in sync with the ViewDefinitions. Never hardcode measure SQL here.
"""

import importlib.resources as pkg
import requests


SOF_SCHEMA = "sof"

RISK_STRATIFICATION_SQL = f"""
SELECT
    aem.source_system_id,
    aem.source_type,
    aem.ecds_ssor,
    aem.entity_type  AS resource_type,
    aem.confidence,
    COUNT(*)         AS resource_count
FROM {SOF_SCHEMA}.audit_event_metadata aem
WHERE aem.source_system_id IS NOT NULL
GROUP BY 1, 2, 3, 4, 5
ORDER BY resource_count DESC
"""

SOURCE_COVERAGE_SQL = f"""
SELECT
    aem.source_system_id,
    aem.source_type,
    aem.ecds_ssor,
    aem.ol_run_id,
    aem.entity_type  AS resource_type,
    COUNT(*)         AS resource_count,
    MIN(aem.recorded) AS earliest_record,
    MAX(aem.recorded) AS latest_record
FROM {SOF_SCHEMA}.audit_event_metadata aem
GROUP BY 1, 2, 3, 4, 5
ORDER BY aem.source_system_id, resource_type
"""

UNKNOWN_SOURCE_SQL = f"""
SELECT
    aem.audit_event_id,
    aem.entity_ref,
    aem.entity_type,
    aem.recorded,
    aem.pipeline_id,
    aem.ol_run_id
FROM {SOF_SCHEMA}.audit_event_metadata aem
WHERE aem.source_type = 'unknown'
   OR aem.source_type IS NULL
ORDER BY aem.recorded DESC
"""


def _load_measure_sql(measure_name: str) -> str:
    sql_file = pkg.files("cdar_contracts") / "sql" / "measures" / f"{measure_name}.sql"
    return sql_file.read_text()


def _run_sql(sql: str, aidbox_sql_url: str, headers: dict) -> list[dict]:
    response = requests.post(
        aidbox_sql_url,
        json=[sql],
        headers={**headers, "Content-Type": "application/json"},
        timeout=120,
    )
    response.raise_for_status()
    rows = response.json()
    if not rows or len(rows) < 2:
        return []
    columns = rows[0]
    return [dict(zip(columns, row)) for row in rows[1:]]


def run_risk_stratification(aidbox_sql_url: str, headers: dict) -> list[dict]:
    """
    Risk stratification matrix: per source_system_id, resource counts by type.

    Replaces the raw LATERAL jsonb_array_elements query in dqar-04 spec.
    Queries sof.audit_event_metadata — requires prior $materialize call.
    """
    return _run_sql(RISK_STRATIFICATION_SQL, aidbox_sql_url, headers)


def run_source_coverage(aidbox_sql_url: str, headers: dict) -> list[dict]:
    """
    Per-source coverage report: resource counts, date ranges, ol_run_id per feed.
    """
    return _run_sql(SOURCE_COVERAGE_SQL, aidbox_sql_url, headers)


def run_unknown_source_report(aidbox_sql_url: str, headers: dict) -> list[dict]:
    """
    Resources where source inference returned unknown — each is a Tier 1 finding.
    """
    return _run_sql(UNKNOWN_SOURCE_SQL, aidbox_sql_url, headers)


def run_cbp_numerator(aidbox_sql_url: str, headers: dict) -> dict:
    """
    CBP numerator reconstruction from cdar-contracts SQL.

    The measure SQL in cdar-contracts joins sof.observation_bp with
    sof.audit_event_metadata to project observation_id + lineage columns.
    """
    sql = _load_measure_sql("cbp_numerator")
    results = _run_sql(sql, aidbox_sql_url, headers)

    numerator_patients = {
        r["patient_id"] for r in results if r.get("cbp_numerator") is True
    }
    return {
        "patients_in_numerator": numerator_patients,
        "results": results,
        "population_count": len(results),
    }


def run_cdc_hba1c_numerator(aidbox_sql_url: str, headers: dict) -> dict:
    """
    CDC HbA1c numerator reconstruction from cdar-contracts SQL.

    The measure SQL joins sof.observation_hba1c with sof.audit_event_metadata.
    Flags observations with plausibility issues as Tier 2 findings.
    """
    sql = _load_measure_sql("cdc_hba1c_numerator")
    results = _run_sql(sql, aidbox_sql_url, headers)

    numerator_patients = {r["patient_id"] for r in results}
    flagged = [r["observation_id"] for r in results if r.get("plausibility_flag") is True]

    return {
        "patients_in_numerator": numerator_patients,
        "results": results,
        "population_count": len(results),
        "flagged_implausible": flagged,
    }


def run_full_assessment(aidbox_sql_url: str, headers: dict) -> dict:
    """
    Run all Stage 4 assessments and return a combined result dict for Stage 5.
    """
    return {
        "risk_stratification":   run_risk_stratification(aidbox_sql_url, headers),
        "source_coverage":       run_source_coverage(aidbox_sql_url, headers),
        "unknown_sources":       run_unknown_source_report(aidbox_sql_url, headers),
        "cbp_numerator":         run_cbp_numerator(aidbox_sql_url, headers),
        "cdc_hba1c_numerator":   run_cdc_hba1c_numerator(aidbox_sql_url, headers),
    }
