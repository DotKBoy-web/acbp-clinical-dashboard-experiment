-- Refresh the existing CBP materialized artifacts before reading them.
-- This reuses the existing 04_cbp_model path and does not modify source schemas.
SELECT cbp.refresh_fac01_all(false);

BEGIN;

DROP TABLE IF EXISTS validity_ext.cbp_observed_surface CASCADE;

CREATE TABLE validity_ext.cbp_observed_surface AS
SELECT
    'CBP_OBSERVED'::text AS source_surface,
    'OBSERVED_CBP'::text AS case_type,

    ef.encntr_id,
    ef.person_id,
    f.facility_key,
    b.building_type,
    ef.loc_nurse_unit_cd,
    ef.loc_room_cd,
    ef.loc_bed_cd,
    ef.inpatient_admit_dt_tm,
    ef.disch_dt_tm,
    dot.first_discharge_order_dt_tm,

    ef.f_admit_today,
    ef.f_disch_today,
    ef.f_census_live,
    ef.f_bedded_census_live,

    CASE
        WHEN ef.f_census_live = 1
         AND dot.first_discharge_order_dt_tm IS NOT NULL
        THEN 1 ELSE 0
    END AS f_has_active_discharge_order,

    false AS injected_invalid,
    NULL::text AS injected_invalid_rule

FROM cbp.fac01_enc_flags_mat ef
JOIN cerner_ref.nurse_unit nu
    ON nu.nurse_unit_cd = ef.loc_nurse_unit_cd
JOIN cerner_ref.building b
    ON b.building_cd = nu.building_cd
JOIN cerner_ref.facility f
    ON f.facility_cd = b.facility_cd
LEFT JOIN cbp.fac01_discharge_order_times_mat dot
    ON dot.encntr_id = ef.encntr_id
WHERE f.facility_key = 'FAC_01'
  AND b.building_type = 'IPD';

CREATE INDEX cbp_observed_surface_enc_idx
    ON validity_ext.cbp_observed_surface (encntr_id);

CREATE INDEX cbp_observed_surface_state_idx
    ON validity_ext.cbp_observed_surface (
        loc_nurse_unit_cd,
        loc_room_cd,
        loc_bed_cd,
        f_census_live,
        f_bedded_census_live,
        f_has_active_discharge_order
    );

COMMIT;
