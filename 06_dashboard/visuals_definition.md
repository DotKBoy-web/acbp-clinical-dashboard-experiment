# Dashboard Visual Definitions

## Page 1: Live SQL Dashboard

Visuals:

- KPI card: census count
- KPI card: discharge count
- KPI card: occupancy ratio
- bar chart: census by nurse unit
- table: facility, building, nurse unit, census, capacity

Filters:

- facility
- building
- nurse unit
- room type

## Page 2: ACBP Dashboard

Use the same visual layout and filters as the live SQL dashboard page.

Purpose:

Preserve metric semantics while changing the execution model.

## Page 3: Performance Comparison

Visuals:

- line chart: live SQL latency over iterations
- line chart: ACBP latency over iterations
- line chart: paired speedup
- table: mean, median, P95 latency

Sources:

    07_metrics_collection/raw_logs/combined_metrics.csv
    08_analysis/stats_summary.md

## Page 4: Buffer Access Comparison

Visuals:

- line chart: shared buffer hits
- line chart: live/ACBP buffer ratio
- KPI card: mean buffer ratio
- KPI card: mean buffer reduction percentage

Sources:

    08_analysis/plots/buffers_hits_timeseries.png
    08_analysis/plots/buffers_ratio_timeseries.png

## Page 5: Resource Context

Visuals:

- line chart: CPU usage
- line chart: memory usage

Purpose:

Show whether improvements are driven by reduced execution cost rather than increased resource usage.