BEGIN;

CREATE SCHEMA IF NOT EXISTS validity_ext;

DROP VIEW IF EXISTS validity_ext.ml_dataset CASCADE;
DROP VIEW IF EXISTS validity_ext.rule_violation_summary CASCADE;
DROP VIEW IF EXISTS validity_ext.case_type_validity_summary CASCADE;
DROP VIEW IF EXISTS validity_ext.dotk_complexity_summary CASCADE;
DROP VIEW IF EXISTS validity_ext.state_surface_labeled CASCADE;
DROP VIEW IF EXISTS validity_ext.state_surface_all CASCADE;

DROP TABLE IF EXISTS validity_ext.synthetic_invalid_space CASCADE;
DROP TABLE IF EXISTS validity_ext.cbp_observed_surface CASCADE;
DROP TABLE IF EXISTS validity_ext.live_observed_surface CASCADE;

COMMIT;
