/* ============================================================================
   CBP MATERIALIZED ARTIFACTS (FAC_01 – IPD)
   Goal: Replace repeated runtime dependency resolution with compiled/materialized
         artifacts that are refreshed, indexed, and joined predictably.

   Produces: cbp.fac01_dashboard_kpis  (same columns as live_dashboard_query.sql)
   ============================================================================ */

BEGIN;

CREATE SCHEMA IF NOT EXISTS cbp;

-- -----------------------------
-- Clean re-run (safe for experiments)
-- -----------------------------
DROP VIEW IF EXISTS cbp.fac01_dashboard_kpis CASCADE;

DROP MATERIALIZED VIEW IF EXISTS cbp.fac01_discharge_order_times_mat CASCADE;
DROP MATERIALIZED VIEW IF EXISTS cbp.fac01_unit_occ_mat CASCADE;
DROP MATERIALIZED VIEW IF EXISTS cbp.fac01_enc_flags_mat CASCADE;

-- ============================================================================
-- 1) CBP “compiled state” materialization: encounter flags, scoped to FAC_01 IPD
--    This is the compiled/normalized state surface for analytics.
-- ============================================================================
CREATE MATERIALIZED VIEW cbp.fac01_enc_flags_mat AS
WITH bounds AS (
  SELECT
    date_trunc('day', now())                    AS start_ts,
    date_trunc('day', now()) + interval '1 day' AS end_ts
),
enc_scope AS (
  SELECT
    e.encntr_id,
    e.person_id,
    e.loc_nurse_unit_cd,
    e.loc_room_cd,
    e.loc_bed_cd,
    e.inpatient_admit_dt_tm,
    e.disch_dt_tm
  FROM cerner.encounter e
  JOIN cerner_ref.nurse_unit nu
    ON nu.nurse_unit_cd = e.loc_nurse_unit_cd
  JOIN cerner_ref.building b
    ON b.building_cd = nu.building_cd
  JOIN cerner_ref.facility f
    ON f.facility_cd = b.facility_cd
  WHERE e.active_ind = 1
    AND e.inpatient_admit_dt_tm IS NOT NULL
    AND f.facility_key = 'FAC_01'
    AND b.building_type = 'IPD'
)
SELECT
  es.*,

  CASE
    WHEN es.inpatient_admit_dt_tm >= b.start_ts
     AND es.inpatient_admit_dt_tm <  b.end_ts
    THEN 1 ELSE 0
  END AS f_admit_today,

  CASE
    WHEN es.disch_dt_tm >= b.start_ts
     AND es.disch_dt_tm <  b.end_ts
    THEN 1 ELSE 0
  END AS f_disch_today,

  CASE
    WHEN es.inpatient_admit_dt_tm <= now()
     AND (es.disch_dt_tm IS NULL OR es.disch_dt_tm > now())
    THEN 1 ELSE 0
  END AS f_census_live,

  CASE
    WHEN es.inpatient_admit_dt_tm <= now()
     AND (es.disch_dt_tm IS NULL OR es.disch_dt_tm > now())
     AND es.loc_room_cd IS NOT NULL
     AND es.loc_bed_cd  IS NOT NULL
    THEN 1 ELSE 0
  END AS f_bedded_census_live

FROM enc_scope es
CROSS JOIN bounds b
WITH NO DATA;

-- Required for REFRESH CONCURRENTLY
CREATE UNIQUE INDEX fac01_enc_flags_mat_uq
  ON cbp.fac01_enc_flags_mat (encntr_id);

CREATE INDEX fac01_enc_flags_mat_unit
  ON cbp.fac01_enc_flags_mat (loc_nurse_unit_cd);

CREATE INDEX fac01_enc_flags_mat_census
  ON cbp.fac01_enc_flags_mat (f_census_live, f_bedded_census_live);

-- ============================================================================
-- 2) CBP occupancy materialization: occupied beds per unit (distinct room,bed)
--    Uses composite DISTINCT to avoid string concat and reduce planner work.
-- ============================================================================
CREATE MATERIALIZED VIEW cbp.fac01_unit_occ_mat AS
SELECT
  ef.loc_nurse_unit_cd,
  COUNT(DISTINCT (ef.loc_room_cd, ef.loc_bed_cd)) AS occ_beds_live
FROM cbp.fac01_enc_flags_mat ef
WHERE ef.f_bedded_census_live = 1
GROUP BY ef.loc_nurse_unit_cd
WITH NO DATA;

CREATE UNIQUE INDEX fac01_unit_occ_mat_uq
  ON cbp.fac01_unit_occ_mat (loc_nurse_unit_cd);

-- ============================================================================
-- 3) CBP discharge order times materialization
-- ============================================================================
CREATE MATERIALIZED VIEW cbp.fac01_discharge_order_times_mat AS
SELECT
  o.encntr_id,
  MIN(o.orig_order_dt_tm) AS first_discharge_order_dt_tm
FROM cerner.orders o
JOIN cerner.order_catalog oc
  ON oc.catalog_cd = o.catalog_cd
 AND oc.catalog_type_cd = o.catalog_type_cd
WHERE o.active_ind = 1
  AND oc.primary_mnemonic = 'Discharge Patient'
GROUP BY o.encntr_id
WITH NO DATA;

CREATE UNIQUE INDEX fac01_discharge_order_times_mat_uq
  ON cbp.fac01_discharge_order_times_mat (encntr_id);

-- ============================================================================
-- 4) Final KPI view (1 row), reading from CBP materialized artifacts
--    Column set matches live_dashboard_query.sql output.
-- ============================================================================
CREATE VIEW cbp.fac01_dashboard_kpis AS
WITH capacity_kpis AS (
  SELECT
    SUM(uc.cap_beds) AS cap_beds,
    SUM(COALESCE(uoc.occ_beds_live,0)) AS occ_beds,
    SUM(uc.cap_beds - COALESCE(uoc.occ_beds_live,0)) AS empty_beds,
    ROUND(
      CASE
        WHEN SUM(uc.cap_beds) = 0 THEN 0
        ELSE (SUM(COALESCE(uoc.occ_beds_live,0))::numeric / SUM(uc.cap_beds)::numeric) * 100
      END,
      2
    ) AS bed_occupancy_percentage
  FROM cerner_ref.unit_capacity uc
  JOIN cerner_ref.nurse_unit nu
    ON nu.nurse_unit_cd = uc.nurse_unit_cd
  JOIN cerner_ref.building b
    ON b.building_cd = nu.building_cd
  JOIN cerner_ref.facility f
    ON f.facility_cd = b.facility_cd
  LEFT JOIN cbp.fac01_unit_occ_mat uoc
    ON uoc.loc_nurse_unit_cd = uc.nurse_unit_cd
  WHERE f.facility_key = 'FAC_01'
    AND b.building_type = 'IPD'
),
overall_kpis AS (
  SELECT
    COUNT(*) AS total_encounters,
    COUNT(DISTINCT person_id) AS unique_patients,
    SUM(f_admit_today) AS admissions_today,
    SUM(f_disch_today) AS discharges_today,
    SUM(f_census_live) AS census_live,
    COUNT(DISTINCT CASE
      WHEN f_bedded_census_live = 1 THEN (loc_room_cd, loc_bed_cd)
      ELSE NULL
    END) AS bedded_census_live,
    ROUND(
      AVG(
        CASE
          WHEN disch_dt_tm IS NOT NULL
          THEN EXTRACT(EPOCH FROM (disch_dt_tm - inpatient_admit_dt_tm)) / 86400.0
        END
      ),
      2
    ) AS avg_los_days
  FROM cbp.fac01_enc_flags_mat
),
discharge_time_kpis AS (
  SELECT
    ROUND(
      AVG(EXTRACT(EPOCH FROM (ef.disch_dt_tm - dot.first_discharge_order_dt_tm)) / 3600.0),
      2
    ) AS avg_time_to_discharge_hours
  FROM cbp.fac01_enc_flags_mat ef
  JOIN cbp.fac01_discharge_order_times_mat dot
    ON dot.encntr_id = ef.encntr_id
  WHERE ef.disch_dt_tm IS NOT NULL
    AND dot.first_discharge_order_dt_tm IS NOT NULL
    AND ef.disch_dt_tm >= dot.first_discharge_order_dt_tm
)
SELECT
  ok.total_encounters,
  ok.unique_patients,
  ok.admissions_today,
  ok.discharges_today,
  ok.census_live,
  ok.bedded_census_live,
  ck.cap_beds,
  ck.occ_beds,
  ck.empty_beds,
  ck.bed_occupancy_percentage,
  ok.avg_los_days,
  dtk.avg_time_to_discharge_hours
FROM overall_kpis ok
CROSS JOIN capacity_kpis ck
CROSS JOIN discharge_time_kpis dtk;

-- ============================================================================
-- 5) Refresh routine
--    Default: try CONCURRENTLY (requires unique indexes above).
-- ============================================================================
CREATE OR REPLACE FUNCTION cbp.refresh_fac01_all(p_concurrently boolean DEFAULT true)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
  IF p_concurrently THEN
    REFRESH MATERIALIZED VIEW CONCURRENTLY cbp.fac01_enc_flags_mat;
    REFRESH MATERIALIZED VIEW CONCURRENTLY cbp.fac01_unit_occ_mat;
    REFRESH MATERIALIZED VIEW CONCURRENTLY cbp.fac01_discharge_order_times_mat;
  ELSE
    REFRESH MATERIALIZED VIEW cbp.fac01_enc_flags_mat;
    REFRESH MATERIALIZED VIEW cbp.fac01_unit_occ_mat;
    REFRESH MATERIALIZED VIEW cbp.fac01_discharge_order_times_mat;
  END IF;
END;
$$;

COMMIT;

-- ----------------------------------------------------------------------------
-- After loading this script, run:
--   SELECT cbp.refresh_fac01_all(true);
-- then:
--   SELECT * FROM cbp.fac01_dashboard_kpis;
-- ----------------------------------------------------------------------------