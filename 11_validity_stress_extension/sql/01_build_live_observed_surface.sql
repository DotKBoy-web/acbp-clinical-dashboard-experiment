BEGIN;

DROP TABLE IF EXISTS validity_ext.live_observed_surface CASCADE;

CREATE TABLE validity_ext.live_observed_surface AS
WITH bounds AS (
    SELECT
        date_trunc('day', now()) AS start_ts,
        date_trunc('day', now()) + interval '1 day' AS end_ts
),
enc_scope AS (
    SELECT
        e.encntr_id,
        e.person_id,
        f.facility_key,
        b.building_type,
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
)
SELECT
    'LIVE_OBSERVED'::text AS source_surface,
    'OBSERVED_LIVE'::text AS case_type,

    es.encntr_id,
    es.person_id,
    es.facility_key,
    es.building_type,
    es.loc_nurse_unit_cd,
    es.loc_room_cd,
    es.loc_bed_cd,
    es.inpatient_admit_dt_tm,
    es.disch_dt_tm,
    dot.first_discharge_order_dt_tm,

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
         AND es.loc_bed_cd IS NOT NULL
        THEN 1 ELSE 0
    END AS f_bedded_census_live,

    CASE
        WHEN es.inpatient_admit_dt_tm <= now()
         AND (es.disch_dt_tm IS NULL OR es.disch_dt_tm > now())
         AND dot.first_discharge_order_dt_tm IS NOT NULL
        THEN 1 ELSE 0
    END AS f_has_active_discharge_order,

    false AS injected_invalid,
    NULL::text AS injected_invalid_rule

FROM enc_scope es
CROSS JOIN bounds b
LEFT JOIN discharge_order_times dot
    ON dot.encntr_id = es.encntr_id;

CREATE INDEX live_observed_surface_enc_idx
    ON validity_ext.live_observed_surface (encntr_id);

CREATE INDEX live_observed_surface_state_idx
    ON validity_ext.live_observed_surface (
        loc_nurse_unit_cd,
        loc_room_cd,
        loc_bed_cd,
        f_census_live,
        f_bedded_census_live,
        f_has_active_discharge_order
    );

COMMIT;
