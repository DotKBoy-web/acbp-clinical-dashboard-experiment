# Results Artifacts

This directory stores final results derived from raw experiment logs.

## Sources

Raw metrics:

    07_metrics_collection/raw_logs/combined_metrics.csv
    07_metrics_collection/raw_logs/cpu.csv
    07_metrics_collection/raw_logs/memory.csv

Analysis:

    08_analysis/analyze_results.py
    08_analysis/stats_summary.md

## Subdirectories

    09_results/
      figures/
      tables/
      key_findings.md

## Reproducibility rule

Do not manually edit result values. Regenerate figures and tables from the raw logs using the analysis script.