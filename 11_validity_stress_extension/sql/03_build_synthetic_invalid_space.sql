BEGIN;

DROP TABLE IF EXISTS validity_ext.synthetic_invalid_space CASCADE;

CREATE TABLE validity_ext.synthetic_invalid_space AS
WITH base AS (
    SELECT *
    FROM validity_ext.live_observed_surface
    ORDER BY encntr_id
    LIMIT 500
),

invalid_bedded_not_live AS (
    SELECT
        'SYNTH_INVALID'::text AS source_surface,
        'BEDDED_NOT_LIVE'::text AS case_type,

        encntr_id,
        person_id,
        facility_key,
        building_type,
        loc_nurse_unit_cd,
        loc_room_cd,
        loc_bed_cd,
        inpatient_admit_dt_tm,
        disch_dt_tm,
        first_discharge_order_dt_tm,

        f_admit_today,
        f_disch_today,
        0 AS f_census_live,
        1 AS f_bedded_census_live,
        f_has_active_discharge_order,

        true AS injected_invalid,
        'f_bedded_census_live implies f_census_live'::text AS injected_invalid_rule
    FROM base
    WHERE loc_room_cd IS NOT NULL
      AND loc_bed_cd IS NOT NULL
    LIMIT 100
),

invalid_bedded_without_bed AS (
    SELECT
        'SYNTH_INVALID'::text AS source_surface,
        'BEDDED_WITH_NULL_ROOM_OR_BED'::text AS case_type,

        encntr_id,
        person_id,
        facility_key,
        building_type,
        loc_nurse_unit_cd,
        NULL::bigint AS loc_room_cd,
        NULL::bigint AS loc_bed_cd,
        inpatient_admit_dt_tm,
        disch_dt_tm,
        first_discharge_order_dt_tm,

        f_admit_today,
        f_disch_today,
        1 AS f_census_live,
        1 AS f_bedded_census_live,
        f_has_active_discharge_order,

        true AS injected_invalid,
        'bedded census requires room and bed'::text AS injected_invalid_rule
    FROM base
    LIMIT 100
),

invalid_active_order_not_live AS (
    SELECT
        'SYNTH_INVALID'::text AS source_surface,
        'ACTIVE_DISCHARGE_ORDER_NOT_LIVE'::text AS case_type,

        encntr_id,
        person_id,
        facility_key,
        building_type,
        loc_nurse_unit_cd,
        loc_room_cd,
        loc_bed_cd,
        inpatient_admit_dt_tm,
        disch_dt_tm,
        COALESCE(first_discharge_order_dt_tm, now() - interval '2 hours') AS first_discharge_order_dt_tm,

        f_admit_today,
        f_disch_today,
        0 AS f_census_live,
        0 AS f_bedded_census_live,
        1 AS f_has_active_discharge_order,

        true AS injected_invalid,
        'active discharge order implies live census'::text AS injected_invalid_rule
    FROM base
    LIMIT 100
),

invalid_temporal_inversion AS (
    SELECT
        'SYNTH_INVALID'::text AS source_surface,
        'DISCHARGE_BEFORE_ADMISSION'::text AS case_type,

        encntr_id,
        person_id,
        facility_key,
        building_type,
        loc_nurse_unit_cd,
        loc_room_cd,
        loc_bed_cd,
        inpatient_admit_dt_tm,
        inpatient_admit_dt_tm - interval '1 hour' AS disch_dt_tm,
        first_discharge_order_dt_tm,

        f_admit_today,
        1 AS f_disch_today,
        0 AS f_census_live,
        0 AS f_bedded_census_live,
        f_has_active_discharge_order,

        true AS injected_invalid,
        'discharge timestamp before admission timestamp'::text AS injected_invalid_rule
    FROM base
    LIMIT 100
),

invalid_location_hierarchy AS (
    SELECT
        'SYNTH_INVALID'::text AS source_surface,
        'LOCATION_HIERARCHY_MISMATCH'::text AS case_type,

        b.encntr_id,
        b.person_id,
        b.facility_key,
        b.building_type,
        b.loc_nurse_unit_cd,
        bad_room.room_cd AS loc_room_cd,
        bad_bed.bed_cd AS loc_bed_cd,
        b.inpatient_admit_dt_tm,
        b.disch_dt_tm,
        b.first_discharge_order_dt_tm,

        b.f_admit_today,
        b.f_disch_today,
        b.f_census_live,
        1 AS f_bedded_census_live,
        b.f_has_active_discharge_order,

        true AS injected_invalid,
        'room or bed does not belong to nurse unit hierarchy'::text AS injected_invalid_rule
    FROM base b
    JOIN LATERAL (
        SELECT r.room_cd, r.nurse_unit_cd
        FROM cerner_ref.room r
        WHERE r.room_type = 'IPD'
          AND r.nurse_unit_cd IS NOT NULL
          AND r.nurse_unit_cd <> b.loc_nurse_unit_cd
        ORDER BY r.room_cd
        LIMIT 1
    ) bad_room ON true
    JOIN LATERAL (
        SELECT bed.bed_cd, bed.room_cd
        FROM cerner_ref.bed bed
        WHERE bed.room_cd <> bad_room.room_cd
        ORDER BY bed.bed_cd
        LIMIT 1
    ) bad_bed ON true
    WHERE b.loc_room_cd IS NOT NULL
      AND b.loc_bed_cd IS NOT NULL
    LIMIT 100
)

SELECT * FROM invalid_bedded_not_live
UNION ALL
SELECT * FROM invalid_bedded_without_bed
UNION ALL
SELECT * FROM invalid_active_order_not_live
UNION ALL
SELECT * FROM invalid_temporal_inversion
UNION ALL
SELECT * FROM invalid_location_hierarchy;

CREATE INDEX synthetic_invalid_space_case_idx
    ON validity_ext.synthetic_invalid_space (case_type);

CREATE INDEX synthetic_invalid_space_state_idx
    ON validity_ext.synthetic_invalid_space (
        loc_nurse_unit_cd,
        loc_room_cd,
        loc_bed_cd,
        f_census_live,
        f_bedded_census_live,
        f_has_active_discharge_order
    );

COMMIT;
