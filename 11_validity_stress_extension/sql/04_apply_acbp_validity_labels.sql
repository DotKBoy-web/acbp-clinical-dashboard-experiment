BEGIN;

DROP VIEW IF EXISTS validity_ext.state_surface_labeled CASCADE;
DROP VIEW IF EXISTS validity_ext.state_surface_all CASCADE;

CREATE VIEW validity_ext.state_surface_all AS
SELECT * FROM validity_ext.live_observed_surface
UNION ALL
SELECT * FROM validity_ext.cbp_observed_surface
UNION ALL
SELECT * FROM validity_ext.synthetic_invalid_space;

CREATE VIEW validity_ext.state_surface_labeled AS
WITH hierarchy AS (
    SELECT
        f.facility_key,
        b.building_type,
        nu.nurse_unit_cd,
        r.room_cd,
        bed.bed_cd
    FROM cerner_ref.facility f
    JOIN cerner_ref.building b
        ON b.facility_cd = f.facility_cd
    JOIN cerner_ref.nurse_unit nu
        ON nu.building_cd = b.building_cd
    LEFT JOIN cerner_ref.room r
        ON r.nurse_unit_cd = nu.nurse_unit_cd
    LEFT JOIN cerner_ref.bed bed
        ON bed.room_cd = r.room_cd
    WHERE f.facility_key = 'FAC_01'
      AND b.building_type = 'IPD'
),
rule_eval AS (
    SELECT
        s.*,

        CASE
            WHEN s.facility_key = 'FAC_01'
             AND s.building_type = 'IPD'
            THEN true ELSE false
        END AS rule_fac01_ipd_scope,

        CASE
            WHEN s.f_bedded_census_live = 1
             AND s.f_census_live = 0
            THEN false ELSE true
        END AS rule_bedded_implies_census,

        CASE
            WHEN s.f_bedded_census_live = 1
             AND (s.loc_room_cd IS NULL OR s.loc_bed_cd IS NULL)
            THEN false ELSE true
        END AS rule_bedded_requires_room_bed,

        CASE
            WHEN s.disch_dt_tm IS NOT NULL
             AND s.inpatient_admit_dt_tm IS NOT NULL
             AND s.disch_dt_tm < s.inpatient_admit_dt_tm
            THEN false ELSE true
        END AS rule_discharge_after_admission,

        CASE
            WHEN s.f_has_active_discharge_order = 1
             AND s.f_census_live = 0
            THEN false ELSE true
        END AS rule_active_order_implies_census,

        CASE
            WHEN s.loc_room_cd IS NULL
             AND s.loc_bed_cd IS NULL
            THEN true
            WHEN s.loc_room_cd IS NULL
              OR s.loc_bed_cd IS NULL
            THEN false
            WHEN EXISTS (
                SELECT 1
                FROM hierarchy h
                WHERE h.facility_key = s.facility_key
                  AND h.building_type = s.building_type
                  AND h.nurse_unit_cd = s.loc_nurse_unit_cd
                  AND h.room_cd = s.loc_room_cd
                  AND h.bed_cd = s.loc_bed_cd
            )
            THEN true ELSE false
        END AS rule_location_hierarchy_valid

    FROM validity_ext.state_surface_all s
)
SELECT
    r.*,

    (
        rule_fac01_ipd_scope
        AND rule_bedded_implies_census
        AND rule_bedded_requires_room_bed
        AND rule_discharge_after_admission
        AND rule_active_order_implies_census
        AND rule_location_hierarchy_valid
    ) AS acbp_valid,

    concat_ws('|',
        COALESCE(facility_key, 'NULL'),
        COALESCE(building_type, 'NULL'),
        COALESCE(loc_nurse_unit_cd::text, 'NULL'),
        COALESCE(loc_room_cd::text, 'NULL'),
        COALESCE(loc_bed_cd::text, 'NULL'),
        f_admit_today::text,
        f_disch_today::text,
        f_census_live::text,
        f_bedded_census_live::text,
        f_has_active_discharge_order::text
    ) AS state_key,

    array_remove(ARRAY[
        CASE WHEN NOT rule_fac01_ipd_scope
             THEN 'FAC01_IPD_SCOPE' END,
        CASE WHEN NOT rule_bedded_implies_census
             THEN 'BEDDED_IMPLIES_CENSUS' END,
        CASE WHEN NOT rule_bedded_requires_room_bed
             THEN 'BEDDED_REQUIRES_ROOM_BED' END,
        CASE WHEN NOT rule_discharge_after_admission
             THEN 'DISCHARGE_AFTER_ADMISSION' END,
        CASE WHEN NOT rule_active_order_implies_census
             THEN 'ACTIVE_ORDER_IMPLIES_CENSUS' END,
        CASE WHEN NOT rule_location_hierarchy_valid
             THEN 'LOCATION_HIERARCHY_VALID' END
    ], NULL) AS violated_rules

FROM rule_eval r;

COMMIT;
