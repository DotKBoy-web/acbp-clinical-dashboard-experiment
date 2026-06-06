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

## Dashboard demo

The dashboard demo exposes semantic BI-style metric objects and direct SQL execution paths. It compares live SQL and ACBP query results, reports latency, and verifies deterministic result hashes for repeated local API hits. Fixed paper cards are separated from fresh local multi-hit measurements.

## Related ACBP project

This repository is linked to the earlier ACBP project page:

- https://dotkboy-web.github.io/acbp/

The earlier ACBP work introduced the SQL-native categorical-Boolean modeling approach for deterministic decision spaces. This repository applies ACBP to a reproducible clinical dashboard experiment with Live SQL vs compiled ACBP execution and a dashboard UI demo.
## Validity-stress extension

This repository includes an isolated validity-stress extension in `11_validity_stress_extension/`.

The extension reuses the same benchmark database and Live SQL / ACBP paths, creates only the isolated `validity_ext` schema, and reports:

- DotK valid/invalid complexity decomposition
- ACBP validity labels
- uncertainty-aware validity ML diagnostic
- 30 repeated stratified splits
- calibration-oriented metrics

Reproduce from the repository root:

    python .\11_validity_stress_extension\scripts\run_validity_stress_pipeline.py --host 127.0.0.1 --port 55432 --db acbp_db --user acbp --password acbp

Key outputs:

- `11_validity_stress_extension/outputs/ml_key_findings.md`
- `11_validity_stress_extension/outputs/dotk_complexity_summary.csv`
- `11_validity_stress_extension/outputs/validity_ml_uncertainty_summary.csv`
- `09_results/validity_ml_key_findings.md`
