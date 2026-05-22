# ACBP Model Notes

This model implements ACBP for inpatient operational analytics.

--------------------------------------------------

## Principles

- Boolean flags encode workflow state
- Categories encode contextual dimensions
- Constraints define valid configurations
- Materialization defines execution

--------------------------------------------------

## Why ACBP Works

- Limited category space
- Deterministic logic
- Precomputed valid states
- Reduced runtime computation

--------------------------------------------------

## Benefits

- ~66% latency reduction
- ~88.5% buffer reduction
- Stable execution
- Exact results

--------------------------------------------------

## Core Idea

Replace runtime computation with pre-materialized state.