BEGIN;

DROP VIEW IF EXISTS validity_ext.rule_violation_summary CASCADE;
DROP VIEW IF EXISTS validity_ext.case_type_validity_summary CASCADE;
DROP VIEW IF EXISTS validity_ext.dotk_complexity_summary CASCADE;

CREATE VIEW validity_ext.dotk_complexity_summary AS
WITH states AS (
    SELECT DISTINCT
        state_key,
        acbp_valid
    FROM validity_ext.state_surface_labeled
),
counts AS (
    SELECT
        COUNT(*) AS d_obs,
        COUNT(*) FILTER (WHERE acbp_valid) AS d_valid_obs,
        COUNT(*) FILTER (WHERE NOT acbp_valid) AS d_invalid_obs
    FROM states
),
row_counts AS (
    SELECT
        COUNT(*) AS row_obs,
        COUNT(*) FILTER (WHERE acbp_valid) AS row_valid_obs,
        COUNT(*) FILTER (WHERE NOT acbp_valid) AS row_invalid_obs
    FROM validity_ext.state_surface_labeled
)
SELECT
    c.d_obs,
    c.d_valid_obs,
    c.d_invalid_obs,

    ROUND(
        CASE
            WHEN c.d_obs = 0 THEN 0
            ELSE (c.d_invalid_obs::numeric / c.d_obs::numeric) * 100
        END,
        2
    ) AS invalid_support_pct,

    ROUND((LN(GREATEST(c.d_obs, 1)) / LN(2))::numeric, 4) AS k_obs,
    ROUND((LN(GREATEST(c.d_valid_obs, 1)) / LN(2))::numeric, 4) AS k_valid,
    ROUND((LN(GREATEST(c.d_invalid_obs, 1)) / LN(2))::numeric, 4) AS k_invalid,

    ROUND(
        (
            (LN(GREATEST(c.d_obs, 1)) / LN(2))
            -
            (LN(GREATEST(c.d_valid_obs, 1)) / LN(2))
        )::numeric,
        4
    ) AS k_gap,

    r.row_obs,
    r.row_valid_obs,
    r.row_invalid_obs,

    ROUND(
        CASE
            WHEN r.row_obs = 0 THEN 0
            ELSE (r.row_invalid_obs::numeric / r.row_obs::numeric) * 100
        END,
        2
    ) AS invalid_row_pct

FROM counts c
CROSS JOIN row_counts r;

CREATE VIEW validity_ext.case_type_validity_summary AS
SELECT
    source_surface,
    case_type,
    COUNT(*) AS rows,
    COUNT(DISTINCT state_key) AS distinct_states,
    COUNT(*) FILTER (WHERE acbp_valid) AS acbp_valid_rows,
    COUNT(*) FILTER (WHERE NOT acbp_valid) AS acbp_invalid_rows,
    ROUND(
        CASE
            WHEN COUNT(*) = 0 THEN 0
            ELSE (COUNT(*) FILTER (WHERE NOT acbp_valid))::numeric / COUNT(*)::numeric * 100
        END,
        2
    ) AS invalid_row_pct
FROM validity_ext.state_surface_labeled
GROUP BY source_surface, case_type
ORDER BY source_surface, case_type;

CREATE VIEW validity_ext.rule_violation_summary AS
SELECT
    violated_rule,
    COUNT(*) AS violating_rows,
    COUNT(DISTINCT state_key) AS violating_distinct_states
FROM (
    SELECT
        state_key,
        unnest(violated_rules) AS violated_rule
    FROM validity_ext.state_surface_labeled
    WHERE NOT acbp_valid
) x
GROUP BY violated_rule
ORDER BY violating_rows DESC, violated_rule;

COMMIT;
