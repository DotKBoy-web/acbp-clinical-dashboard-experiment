# Dependency Graph (FAC_01 – IPD)

This describes relationships between timestamps, Boolean state, and KPIs.

--------------------------------------------------

## Flow

inpatient_admit_dt_tm → f_census_live  
disch_dt_tm → f_census_live  

f_census_live → f_bedded_census_live  
loc_room_cd → f_bedded_census_live  
loc_bed_cd → f_bedded_census_live  

f_bedded_census_live → occupancy  
occupancy → bed KPI  

f_census_live → census KPI  
inpatient_admit_dt_tm → admissions KPI  
disch_dt_tm → discharges KPI  

first_discharge_order_dt_tm → discharge timing KPI  

--------------------------------------------------

## Interpretation

The model captures:

- time → state transitions  
- state + location → occupancy  
- occupancy → KPI computation  

ACBP materializes these relationships to eliminate recomputation.