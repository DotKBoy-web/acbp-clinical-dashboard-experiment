-- live_base_encounter.sql
-- Base inpatient encounter extract (FAC_01 IPD only)

SELECT
  e.encntr_id,
  e.person_id,
  e.inpatient_admit_dt_tm,
  e.disch_dt_tm,
  e.loc_facility_cd,
  e.loc_building_cd,
  e.loc_nurse_unit_cd,
  e.loc_room_cd,
  e.loc_bed_cd
FROM cerner.encounter e
JOIN cerner_ref.nurse_unit nu ON nu.nurse_unit_cd = e.loc_nurse_unit_cd
JOIN cerner_ref.building b ON b.building_cd = nu.building_cd
JOIN cerner_ref.facility f ON f.facility_cd = b.facility_cd
WHERE e.active_ind = 1
  AND e.inpatient_admit_dt_tm IS NOT NULL
  AND f.facility_key = 'FAC_01'
  AND b.building_type = 'IPD';
``