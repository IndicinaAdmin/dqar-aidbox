/*
 * Controlling High Blood Pressure (CBP) Quality Measure
 *
 * Specification: CMS165v12 / HEDIS CBP
 *   https://ecqi.healthit.gov/ecqm/ec/2024/cms165fhir
 *   https://store.ncqa.org/index.php/performance-measures/hedis.html
 *
 * Denominator:
 *   Patients aged 18–85 with an active hypertension diagnosis.
 *   Codes: SNOMED 38341003 (Hypertensive disorder), ICD-10 I10 (Essential hypertension)
 *
 * Denominator Exclusions:
 *   ESRD (SNOMED 46177005, ICD-10 N18.6)
 *   Renal transplant (SNOMED 175901007, 161665007)
 *   Pregnancy (SNOMED 77386006)
 *   Hospice care (active)
 *
 * Numerator:
 *   Most recent blood pressure reading: systolic < 140 AND diastolic < 90 mmHg.
 *   BP codes: LOINC 55284-4 (panel), 8480-6 (systolic), 8462-4 (diastolic)
 *
 * Provenance metadata output per qualifying event:
 *   source_type, source_system_id, source_feed_id, confidence, ecds_ssor (EXT 1–5)
 *   pipeline_id, ol_run_id (EXT 6–7)
 *
 * Run via Aidbox /$sql endpoint (single-statement CTE chain).
 * Joins sof.audit_event_metadata for per-event provenance metadata.
 *
 * NOTE — Aidbox internal format differences from FHIR JSON:
 *   FHIR effectiveDateTime → resource->'effective'->'dateTime'
 *   FHIR valueQuantity     → resource->'value'->'Quantity'->{value,unit}
 *   FHIR component[].valueQuantity → component[]->'value'->'Quantity'
 *   FHIR Reference {reference:"Patient/X"} → {id:"X", resourceType:"Patient"}
 */

WITH

/* ─── Denominator ──────────────────────────────────────────────────────────
   Active hypertension diagnosis, patient age 18–85.
   Age calculated from year-only birthDate (Synthea/HAPI convention). */
denom AS (
  SELECT DISTINCT ON (p.id, c.id)
    p.id                                                              AS patient_id,
    p.resource->>'gender'                                             AS gender,
    p.resource->>'birthDate'                                          AS birth_date,
    CASE
      WHEN p.resource->>'birthDate' ~ '^\d{4}$'
        THEN (EXTRACT(YEAR FROM CURRENT_DATE)
              - (p.resource->>'birthDate')::int)::int
      WHEN p.resource->>'birthDate' ~ '^\d{4}-\d{2}-\d{2}$'
        THEN EXTRACT(YEAR FROM AGE((p.resource->>'birthDate')::date))::int
      ELSE NULL
    END                                                               AS approx_age,

    -- Qualifying diagnosis
    c.id                                                              AS dx_condition_id,
    c.resource->'code'->'coding'->0->>'code'                          AS dx_code,
    c.resource->'code'->'coding'->0->>'system'                        AS dx_code_system,
    c.resource->'code'->'coding'->0->>'display'                       AS diagnosis,
    c.resource->>'recordedDate'                                       AS dx_recorded_date,

    -- EXT 1–5: provenance of the qualifying diagnosis
    dx_meta.source_type                                               AS dx_source_type,
    dx_meta.source_system_id                                          AS dx_source_system_id,
    dx_meta.source_feed_id                                            AS dx_source_feed_id,
    dx_meta.confidence                                                AS dx_confidence,
    dx_meta.ecds_ssor                                                 AS dx_ecds_ssor,
    -- EXT 6–7: pipeline lineage
    dx_meta.pipeline_id                                               AS dx_pipeline_id,
    dx_meta.ol_run_id                                                 AS dx_ol_run_id

  FROM patient p
  JOIN condition c ON c.resource->'subject'->>'id' = p.id
  -- One audit event per condition — use most recent for the target pipeline
  LEFT JOIN LATERAL (
    SELECT source_type, source_system_id, source_feed_id,
           confidence, ecds_ssor, pipeline_id, ol_run_id
    FROM sof.audit_event_metadata
    WHERE entity_id   = c.id
      AND entity_type = 'Condition'
      AND pipeline_id = 'pipeline-0.1.1-test'
    ORDER BY recorded DESC
    LIMIT 1
  ) dx_meta ON true

  WHERE
    -- Active clinical status
    c.resource->'clinicalStatus'->'coding'->0->>'code' = 'active'
    -- Hypertension codes
    AND (
      c.resource->'code'->'coding'->0->>'code' IN ('38341003', 'I10')
      OR c.resource->'code'->'coding'->0->>'display' ILIKE '%hypertens%'
    )
    -- Age 18–85
    AND CASE
      WHEN p.resource->>'birthDate' ~ '^\d{4}$'
        THEN (EXTRACT(YEAR FROM CURRENT_DATE)
              - (p.resource->>'birthDate')::int)
      WHEN p.resource->>'birthDate' ~ '^\d{4}-\d{2}-\d{2}$'
        THEN EXTRACT(YEAR FROM AGE((p.resource->>'birthDate')::date))
      ELSE NULL
    END BETWEEN 18 AND 85
),


/* ─── Denominator Exclusions ────────────────────────────────────────────── */
exclusions AS (
  SELECT DISTINCT ON (c.resource->'subject'->>'id')
    c.resource->'subject'->>'id'                                      AS patient_id,
    c.resource->'code'->'coding'->0->>'code'                          AS exc_code,
    c.resource->'code'->'coding'->0->>'display'                       AS exclusion_reason,
    exc_meta.source_type                                              AS exc_source_type,
    exc_meta.source_system_id                                         AS exc_source_system_id,
    exc_meta.confidence                                               AS exc_confidence,
    exc_meta.ecds_ssor                                                AS exc_ecds_ssor

  FROM condition c
  LEFT JOIN LATERAL (
    SELECT source_type, source_system_id, confidence, ecds_ssor
    FROM sof.audit_event_metadata
    WHERE entity_id   = c.id
      AND entity_type = 'Condition'
      AND pipeline_id = 'pipeline-0.1.1-test'
    ORDER BY recorded DESC
    LIMIT 1
  ) exc_meta ON true

  WHERE c.resource->'clinicalStatus'->'coding'->0->>'code' = 'active'
    AND (
      -- ESRD: SNOMED 46177005 / ICD-10 N18.x
      c.resource->'code'->'coding'->0->>'code' IN ('46177005', 'N18.6')
      -- Renal transplant: SNOMED 175901007 (procedure) or 161665007 (history)
      OR c.resource->'code'->'coding'->0->>'code' IN ('175901007', '161665007')
      -- Pregnancy: SNOMED 77386006
      OR c.resource->'code'->'coding'->0->>'code' = '77386006'
      -- Text fallbacks for poorly-coded data
      OR c.resource->'code'->'coding'->0->>'display' ILIKE '%end-stage renal%'
      OR c.resource->'code'->'coding'->0->>'display' ILIKE '%ESRD%'
      OR c.resource->'code'->'coding'->0->>'display' ILIKE '%renal transplant%'
      OR c.resource->'code'->'coding'->0->>'display' ILIKE '%pregnant%'
      OR c.resource->'code'->'coding'->0->>'display' ILIKE '%hospice%'
    )
),


/* ─── Most-Recent Blood Pressure Reading ──────────────────────────────────
   Handles two storage patterns from this dataset:
   A) BP panel (55284-4) with component array → systolic 8480-6 / diastolic 8462-4
   B) Single-value BP (55284-4) → resource->'value'->'Quantity'->>'value' (systolic only)

   Aidbox internal format: valueQuantity is stored under 'value'->'Quantity'. */
latest_bp AS (
  SELECT DISTINCT ON (o.resource->'subject'->>'id')
    o.id                                                              AS obs_id,
    o.resource->'subject'->>'id'                                      AS patient_id,
    o.resource->'effective'->>'dateTime'                              AS bp_date,

    -- Systolic: component (panel) → scalar fallback
    COALESCE(
      (SELECT (comp->'value'->'Quantity'->>'value')::numeric
       FROM jsonb_array_elements(o.resource->'component') comp
       WHERE comp->'code'->'coding'->0->>'code' = '8480-6'
       LIMIT 1),
      (o.resource->'value'->'Quantity'->>'value')::numeric
    )                                                                 AS systolic_mmhg,

    -- Diastolic: component only (no scalar fallback for this code)
    (SELECT (comp->'value'->'Quantity'->>'value')::numeric
     FROM jsonb_array_elements(o.resource->'component') comp
     WHERE comp->'code'->'coding'->0->>'code' = '8462-4'
     LIMIT 1)                                                         AS diastolic_mmhg,

    -- EXT 1–5: provenance of the BP reading
    bp_meta.source_type                                               AS bp_source_type,
    bp_meta.source_system_id                                          AS bp_source_system_id,
    bp_meta.source_feed_id                                            AS bp_source_feed_id,
    bp_meta.confidence                                                AS bp_confidence,
    bp_meta.ecds_ssor                                                 AS bp_ecds_ssor,
    -- EXT 6–7
    bp_meta.pipeline_id                                               AS bp_pipeline_id,
    bp_meta.ol_run_id                                                 AS bp_ol_run_id

  FROM observation o
  LEFT JOIN LATERAL (
    SELECT source_type, source_system_id, source_feed_id,
           confidence, ecds_ssor, pipeline_id, ol_run_id
    FROM sof.audit_event_metadata
    WHERE entity_id   = o.id
      AND entity_type = 'Observation'
      AND pipeline_id = 'pipeline-0.1.1-test'
    ORDER BY recorded DESC
    LIMIT 1
  ) bp_meta ON true

  WHERE
    o.resource @> '{"code":{"coding":[{"code":"55284-4"}]}}'
    OR o.resource @> '{"code":{"coding":[{"code":"8480-6"}]}}'

  ORDER BY
    o.resource->'subject'->>'id',
    o.resource->'effective'->>'dateTime' DESC NULLS LAST
),


/* ─── Measure Result per Patient ──────────────────────────────────────────
   Assembles denominator + exclusions + numerator into one row per patient.
   CBP result follows CMS165v12 logic with data-quality notes for sparse values. */
measure AS (
  SELECT
    d.patient_id,
    d.gender,
    d.birth_date,
    d.approx_age,

    -- Population status
    CASE WHEN e.patient_id IS NOT NULL THEN 'EXCLUDED'
         ELSE 'IN DENOMINATOR'
    END                                                               AS population,

    -- Numerator classification
    CASE
      WHEN e.patient_id IS NOT NULL
        THEN 'EXCLUDED — ' || e.exclusion_reason
      WHEN bp.obs_id IS NULL
        THEN 'NOT IN NUMERATOR — No BP reading on record'
      WHEN bp.systolic_mmhg IS NULL
        THEN 'NOT IN NUMERATOR — BP record exists, values not captured'
      WHEN bp.diastolic_mmhg IS NULL AND bp.systolic_mmhg < 140
        THEN 'INDETERMINATE — Systolic ' || bp.systolic_mmhg || ' mmHg (controlled); diastolic not captured'
      WHEN bp.diastolic_mmhg IS NULL AND bp.systolic_mmhg >= 140
        THEN 'NOT IN NUMERATOR — Systolic ' || bp.systolic_mmhg || ' mmHg (uncontrolled); diastolic not captured'
      WHEN bp.systolic_mmhg < 140 AND bp.diastolic_mmhg < 90
        THEN 'IN NUMERATOR — Controlled (' || bp.systolic_mmhg || '/' || bp.diastolic_mmhg || ' mmHg)'
      ELSE
        'NOT IN NUMERATOR — Uncontrolled (' || bp.systolic_mmhg || '/' || COALESCE(bp.diastolic_mmhg::text, '?') || ' mmHg)'
    END                                                               AS cbp_result,

    -- ── Denominator qualifying event ──────────────────────────────────────
    d.dx_condition_id,
    d.dx_code,
    d.dx_code_system,
    d.diagnosis,
    d.dx_recorded_date,
    -- Provenance metadata (EXT 1–5)
    d.dx_source_type,
    d.dx_source_system_id,
    d.dx_source_feed_id,
    d.dx_confidence,
    d.dx_ecds_ssor,
    -- Pipeline metadata (EXT 6–7)
    d.dx_pipeline_id,
    d.dx_ol_run_id,

    -- ── Exclusion event (if applicable) ───────────────────────────────────
    e.exc_code,
    e.exclusion_reason,
    e.exc_source_type,
    e.exc_source_system_id,
    e.exc_confidence,
    e.exc_ecds_ssor,

    -- ── Numerator qualifying event (BP reading) ────────────────────────────
    bp.obs_id                                                         AS bp_obs_id,
    bp.bp_date,
    bp.systolic_mmhg,
    bp.diastolic_mmhg,
    -- Provenance metadata (EXT 1–5)
    bp.bp_source_type,
    bp.bp_source_system_id,
    bp.bp_source_feed_id,
    bp.bp_confidence,
    bp.bp_ecds_ssor,
    -- Pipeline metadata (EXT 6–7)
    bp.bp_pipeline_id,
    bp.bp_ol_run_id

  FROM denom d
  LEFT JOIN exclusions e ON e.patient_id = d.patient_id
  LEFT JOIN latest_bp bp ON bp.patient_id = d.patient_id
)

/* ─── Final Output ──────────────────────────────────────────────────────── */
SELECT
  patient_id,
  gender,
  approx_age,
  population,
  cbp_result,

  -- Denominator qualifying event + provenance
  dx_condition_id,
  dx_code,
  dx_code_system,
  diagnosis,
  dx_recorded_date,
  dx_source_type,
  dx_source_system_id,
  dx_source_feed_id,
  dx_confidence,
  dx_ecds_ssor,
  dx_pipeline_id,
  dx_ol_run_id,

  -- Exclusion event + provenance (NULL if patient is not excluded)
  exc_code,
  exclusion_reason,
  exc_source_type,
  exc_source_system_id,
  exc_confidence,
  exc_ecds_ssor,

  -- Numerator qualifying BP event + provenance (NULL if no reading)
  bp_obs_id,
  bp_date,
  systolic_mmhg,
  diastolic_mmhg,
  bp_source_type,
  bp_source_system_id,
  bp_source_feed_id,
  bp_confidence,
  bp_ecds_ssor,
  bp_pipeline_id,
  bp_ol_run_id

FROM measure
ORDER BY population, cbp_result, patient_id;
