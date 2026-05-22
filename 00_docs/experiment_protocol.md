# Experiment Protocol

This document defines the procedure used to evaluate ACBP vs Live SQL execution.

--------------------------------------------------

## 1. Objective

Compare performance and correctness between:

- Live SQL execution (baseline)
- ACBP compiled execution

--------------------------------------------------

## 2. Setup

- Load synthetic inpatient dataset (FAC_01)
- Initialize PostgreSQL database
- Apply schema and indexes

--------------------------------------------------

## 3. ACBP Preparation

Execute:

cbp_materialization.sql

This produces:

- Boolean state tables
- Decision space artifacts
- Materialized KPI views

--------------------------------------------------

## 4. Execution Steps

### Step 1 — Refresh State

SELECT cbp.refresh_fac01_all(true);

### Step 2 — Run Live Query

SELECT * FROM live_dashboard_query;

Capture:
- Execution time
- Buffer usage

### Step 3 — Run ACBP Query

SELECT * FROM cbp.fac01_dashboard_kpis;

Capture:
- Execution time
- Buffer usage

--------------------------------------------------

## 5. Repetition

- Run both queries multiple iterations
- Ensure warm-cache conditions
- Record all measurements

--------------------------------------------------

## 6. Metrics Collected

- Execution time (ms)
- Shared buffer hits
- Output hash (correctness validation)

--------------------------------------------------

## 7. Validation

- Compare outputs between methods
- Verify exact match
- Confirm no missing rows or discrepancies

--------------------------------------------------

## 8. Expected Outcome

- ACBP shows reduced execution time
- ACBP shows reduced buffer usage
- Outputs remain identical

--------------------------------------------------

## Key Property

The protocol isolates the impact of execution model differences while holding data and logic constant.