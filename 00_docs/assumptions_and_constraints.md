# Assumptions and Constraints

This document summarizes the assumptions and constraints underlying the ACBP Clinical Dashboard experiment.

--------------------------------------------------

## 1. Data Assumptions

- The dataset is synthetically generated but structurally aligned with Cerner-like inpatient systems.
- All timestamps (admission, discharge, orders) are internally consistent.
- Each encounter has a valid lifecycle: admit → (optional events) → discharge.
- Facility scope is limited to a single site (FAC_01).

--------------------------------------------------

## 2. Model Assumptions

- Boolean flags are deterministic functions of data fields.
- Categorical dimensions are finite and enumerable.
- Constraints fully define valid workflow states.
- No conflicting rules exist in the constraint set.

--------------------------------------------------

## 3. Execution Assumptions

- PostgreSQL executes all queries under comparable runtime conditions.
- Buffer cache behavior is consistent across runs.
- Materialized views accurately reflect latest data after refresh.

--------------------------------------------------

## 4. ACBP-Specific Constraints

- Valid masks are strictly derived as projection of decision space.
- Invalid state combinations are excluded at compile-time.
- Decision space is finite and fully enumerable.

--------------------------------------------------

## 5. Experimental Constraints

- Single-node execution environment
- No distributed processing
- Synthetic workload only (no real patient data)

--------------------------------------------------

## 6. Limitations

- Does not capture real-world data irregularities
- Does not test extreme category explosion scenarios
- Does not include streaming or real-time ingestion

--------------------------------------------------

## Key Takeaway

These assumptions ensure a controlled environment where ACBP performance improvements can be measured clearly and reproducibly.
