-- live_census_logic.sql
-- Runtime census state resolution

SELECT
  *,
  CASE
    WHEN inpatient_admit_dt_tm <= now()
     AND (disch_dt_tm IS NULL OR disch_dt_tm > now())
    THEN 1 ELSE 0
  END AS f_census_live,

  CASE
    WHEN inpatient_admit_dt_tm <= now()
     AND (disch_dt_tm IS NULL OR disch_dt_tm > now())
     AND loc_room_cd IS NOT NULL
     AND loc_bed_cd IS NOT NULL
    THEN 1 ELSE 0
  END AS f_bedded_census_live
FROM live_base_encounter;
``