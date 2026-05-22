# Dashboard Artifacts

This directory documents the dashboard layer used to interpret the live SQL and ACBP query paths.

The dashboard is not the source of correctness. Correctness is established by deterministic paired result hashes in the metrics pipeline.

## Contents

Directory structure:

    06_dashboard/
      interaction_script.md
      visuals_definition.md
      powerbi/

## Dashboard goals

The dashboard compares live SQL and ACBP execution paths for the same operational metrics:

- Census count
- Bedded census count
- Discharge count
- Unit-level census
- Facility-level census
- Occupancy ratio

## Design principle

Both dashboard paths must use equivalent metric semantics. Any difference in runtime should come from the execution model, not from different metric definitions.