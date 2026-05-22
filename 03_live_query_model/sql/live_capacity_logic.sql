-- live_capacity_logic.sql
-- Runtime bed capacity and occupancy

WITH unit_occ AS (
  SELECT
    loc_nurse_unit_cd,
    COUNT(DISTINCT (loc_room_cd, loc_bed_cd)) AS occ_beds
  FROM live_census_logic
  WHERE f_bedded_census_live = 1
  GROUP BY loc_nurse_unit_cd
)
SELECT
  SUM(uc.cap_beds) AS cap_beds,
  SUM(COALESCE(uo.occ_beds, 0)) AS occ_beds,
  SUM(uc.cap_beds - COALESCE(uo.occ_beds, 0)) AS empty_beds
FROM cerner_ref.unit_capacity uc
LEFT JOIN unit_occ uo
  ON uo.loc_nurse_unit_cd = uc.nurse_unit_cd;