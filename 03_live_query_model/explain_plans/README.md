# Live SQL Explain Plans

This directory stores execution-plan evidence for the live SQL baseline.

The live SQL baseline computes dashboard state directly from transactional and temporal tables at query time. Its plan is expected to include joins, predicate evaluation, aggregation, and buffer access over base tables.

## Source query

    03_live_query_model/sql/live_dashboard_explain.sql

## Recommended output files

    live_dashboard_explain_text.txt
    live_dashboard_explain_json.json
    live_dashboard_buffers_summary.md

## Capture example

    psql -h 127.0.0.1 -p 55432 -U acbp -d acbp_db -f ../sql/live_dashboard_explain.sql > live_dashboard_explain_text.txt

## Record these fields

- Planning time
- Execution time
- Shared buffer hits
- Shared buffer reads
- Join operators
- Scan operators
- Aggregate operators

## Interpretation

This plan is the runtime baseline. Compare it with the ACBP plan under the same data state.