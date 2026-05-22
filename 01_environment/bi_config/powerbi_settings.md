# Power BI Configuration Notes

This document records the Power BI configuration used to mirror the ACBP clinical dashboard experiment.

The dashboard compares two execution paths over the same operational state:

1. Live SQL path: metrics are computed directly from transactional and temporal tables.
2. ACBP path: metrics are computed from precomputed state surfaces and materialized decision structures.

## Data source

- Database engine: PostgreSQL
- Recommended connection mode: DirectQuery
- Schemas:
  - cerner
  - cerner_ref
  - ACBP materialized objects/views from 04_cbp_model/sql

## Live SQL query source

    03_live_query_model/sql/live_dashboard_query.sql

## ACBP query source

    04_cbp_model/sql/cbp_dashboard_query.sql

## Recommended report pages

- Live SQL Dashboard
- ACBP Dashboard
- Performance Comparison
- Buffer Access Comparison
- Resource Utilization

## Recommended slicers

- Facility
- Building
- Nurse Unit
- Room
- Bed
- Iteration
- Query path

## Validation note

Power BI is not the correctness source of truth. Correctness is verified using deterministic paired result hashes in the metrics pipeline.

## Design rule

Do not add Power BI transformations that change SQL metric semantics.