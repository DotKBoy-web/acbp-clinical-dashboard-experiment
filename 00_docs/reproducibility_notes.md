# Reproducibility Notes

This document describes how reproducibility is ensured in the ACBP experiment.

--------------------------------------------------

## 1. Deterministic Logic

- All Boolean flags are deterministic
- No randomness in query logic
- Same input produces identical output

--------------------------------------------------

## 2. Controlled Dataset

- Synthetic dataset generated with fixed schema
- Same structure across all runs
- No external dependencies

--------------------------------------------------

## 3. Fixed Execution Environment

- Single PostgreSQL instance
- Consistent configuration
- No distributed variability

--------------------------------------------------

## 4. Materialization Consistency

- All materialized views refreshed before execution
- Ensures data consistency
- Eliminates stale data issues

--------------------------------------------------

## 5. Repeatability

- Multiple iterations of execution
- Same queries
- Same environment

--------------------------------------------------

## 6. Validation Method

- Result hashing used for correctness
- Ensures exact equality between methods

--------------------------------------------------

## 7. Observability

- Execution time recorded
- Buffer usage recorded
- Logs stored in results directory

--------------------------------------------------

## 8. Known Variations

- Minor timing differences may occur due to system load
- Buffer cache warming may affect initial runs

--------------------------------------------------

## Conclusion

The experiment is fully reproducible under identical setup, dataset, and execution conditions.