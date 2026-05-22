# ACBP Explain Plans

This directory stores execution-plan evidence for the ACBP query path.

The ACBP path executes dashboard logic over precomputed state surfaces and materialized decision structures. It is expected to require fewer runtime joins, fewer predicate evaluations, and fewer shared buffer accesses than live SQL.

## Source query

    04_cbp_model/sql/cbp_dashboard_explain.sql

## Recommended output files

    cbp_dashboard_explain_text.txt
    cbp_dashboard_explain_json.json
    cbp_dashboard_buffers_summary.md

## Capture example

    psql -h 127.0.0.1 -p 55432 -U acbp -d acbp_db -f ../sql/cbp_dashboard_explain.sql > cbp_dashboard_explain_text.txt

## Record these fields

- Planning time
- Execution time
- Shared buffer hits
- Shared buffer reads
- State-surface scan operators
- Decision-space joins
- Aggregate operators

## Interpretation

Compare this plan with the live SQL plan under paired execution conditions. Buffer reduction supports the mechanism claim.