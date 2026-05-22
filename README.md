# ACBP Clinical Dashboard Experiment

This repository contains the reproducibility artifact for the ACBP Clinical Dashboard Experiment submitted to the ICDM 2026 Applied Track. It includes schema creation, synthetic inpatient data generation, live SQL baseline queries, ACBP compiled-state SQL artifacts, feed simulation scripts, metrics collection, analysis scripts, generated plots, and a browser-based dashboard UI demo comparing semantic and direct SQL execution modes.

## Artifact layout

- `00_docs/`: assumptions, protocol, metric definitions, reproducibility notes
- `01_environment/`: software versions, hardware specifications, BI configuration notes
- `02_data_generation/`: schema, seeded generator, and seed configurations
- `03_live_query_model/`: live SQL baseline and explain scripts
- `04_cbp_model/`: ACBP state definitions, materialized views, refresh procedure, and query path
- `05_live_feed_simulation/`: admission, discharge, transfer, and feed simulation
- `06_dashboard/`: Power BI notes and browser-based UI demo
- `07_metrics_collection/`: metric collectors and raw logs
- `08_analysis/`: analysis scripts and plots
- `09_results/`: final figures, tables, and key findings
- `10_paper/`: LaTeX paper source and compiled draft

## Dashboard demo

The dashboard demo exposes semantic BI-style metric objects and direct SQL execution paths. It compares live SQL and ACBP query results, reports latency, and verifies deterministic result hashes for repeated local API hits. Fixed paper cards are separated from fresh local multi-hit measurements.