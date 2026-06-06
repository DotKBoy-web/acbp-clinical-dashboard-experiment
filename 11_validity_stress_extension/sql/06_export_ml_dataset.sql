BEGIN;

DROP VIEW IF EXISTS validity_ext.ml_dataset CASCADE;

CREATE VIEW validity_ext.ml_dataset AS
SELECT
    source_surface,
    case_type,
    injected_invalid,
    injected_invalid_rule,

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
    f_census_live,
    f_bedded_census_live,
    f_has_active_discharge_order,

    CASE WHEN loc_room_cd IS NULL THEN 1 ELSE 0 END AS x_room_missing,
    CASE WHEN loc_bed_cd IS NULL THEN 1 ELSE 0 END AS x_bed_missing,
    CASE
        WHEN disch_dt_tm IS NOT NULL
         AND inpatient_admit_dt_tm IS NOT NULL
        THEN EXTRACT(EPOCH FROM (disch_dt_tm - inpatient_admit_dt_tm)) / 3600.0
        ELSE NULL
    END AS x_los_hours,

    rule_fac01_ipd_scope::int AS rule_fac01_ipd_scope,
    rule_bedded_implies_census::int AS rule_bedded_implies_census,
    rule_bedded_requires_room_bed::int AS rule_bedded_requires_room_bed,
    rule_discharge_after_admission::int AS rule_discharge_after_admission,
    rule_active_order_implies_census::int AS rule_active_order_implies_census,
    rule_location_hierarchy_valid::int AS rule_location_hierarchy_valid,

    acbp_valid::int AS target_acbp_valid,
    violated_rules

FROM validity_ext.state_surface_labeled;

COMMIT;
