# Boolean Flags (FAC_01 – IPD)

These flags define the Boolean state representation in ACBP.

--------------------------------------------------

## Definitions

f_admit_today
1 if admission occurs today

f_disch_today
1 if discharge occurs today

f_census_live
1 if the patient is currently admitted

f_bedded_census_live
1 if the patient occupies a bed

f_has_discharge_order
1 if a discharge order exists

--------------------------------------------------

## Model Mapping

These flags form:

F ∈ {0,1}^B

They represent workflow state in a deterministic form.