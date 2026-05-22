/* ============================================================================
 CBP DASHBOARD KPI QUERY – EXPLAIN ANALYZE
 Same KPI bundle as Live, but via CBP materialized artifacts
 ============================================================================ */
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT *
FROM cbp.fac01_dashboard_kpis;