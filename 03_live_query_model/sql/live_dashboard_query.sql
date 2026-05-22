/* ============================================================================
   LIVE DASHBOARD KPI QUERY (FAC_01 – IPD)
   Baseline "Live SQL" implementation (no precomputation)
   ============================================================================ */

WITH
bounds AS (
  SELECT
    date_trunc('day', now())                    AS start_ts,
    date_trunc('day', now()) + interval '1 day' AS end_ts
),

-- Scope encounters to FAC_01 IPD
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
),

-- Compute live flags
enc_flags AS (
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
),

-- Unit-level occupied beds
unit_census_live AS (
  SELECT
    ef.loc_nurse_unit_cd,
    COUNT(DISTINCT (ef.loc_room_cd::text || '|' || ef.loc_bed_cd::text)) AS occ_beds_live
  FROM enc_flags ef
  WHERE ef.f_bedded_census_live = 1
  GROUP BY ef.loc_nurse_unit_cd
),

-- Capacity KPIs
capacity_kpis AS (
  SELECT
    SUM(uc.cap_beds) AS cap_beds,
    SUM(COALESCE(ucl.occ_beds_live,0)) AS occ_beds,
    SUM(uc.cap_beds - COALESCE(ucl.occ_beds_live,0)) AS empty_beds,
    ROUND(
      CASE
        WHEN SUM(uc.cap_beds) = 0 THEN 0
        ELSE (SUM(COALESCE(ucl.occ_beds_live,0))::numeric / SUM(uc.cap_beds)::numeric) * 100
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
  LEFT JOIN unit_census_live ucl
    ON ucl.loc_nurse_unit_cd = uc.nurse_unit_cd
  WHERE f.facility_key = 'FAC_01'
    AND b.building_type = 'IPD'
),

-- Overall KPIs
overall_kpis AS (
  SELECT
    COUNT(*) AS total_encounters,
    COUNT(DISTINCT person_id) AS unique_patients,
    SUM(f_admit_today) AS admissions_today,
    SUM(f_disch_today) AS discharges_today,
    SUM(f_census_live) AS census_live,

    -- ✅ Correct: bedded census as occupied beds (distinct room|bed)
    COUNT(DISTINCT (CASE
      WHEN f_bedded_census_live = 1
      THEN (loc_room_cd::text || '|' || loc_bed_cd::text)
      ELSE NULL
    END)) AS bedded_census_live,

    ROUND(
      AVG(
        CASE
          WHEN disch_dt_tm IS NOT NULL
          THEN EXTRACT(EPOCH FROM (disch_dt_tm - inpatient_admit_dt_tm)) / 86400.0
        END
      ),
      2
    ) AS avg_los_days
  FROM enc_flags
),

-- Discharge order timing
discharge_order_times AS (
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
),

discharge_time_kpis AS (
  SELECT
    ROUND(
      AVG(
        EXTRACT(EPOCH FROM (ef.disch_dt_tm - dot.first_discharge_order_dt_tm)) / 3600.0
      ),
      2
    ) AS avg_time_to_discharge_hours
  FROM enc_flags ef
  JOIN discharge_order_times dot
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