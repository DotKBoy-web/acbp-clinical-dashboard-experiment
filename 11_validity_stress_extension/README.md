# Validity-Stress Extension

This folder contains the ACBP validity-stress and DotK extension.

It uses the same benchmark database and schema paths as the main experiment, but creates an isolated PostgreSQL schema:

- validity_ext

The source schemas are not modified:

- cerner
- cerner_ref
- cbp

## Purpose

The main benchmark compares Live SQL and ACBP for dashboard correctness, latency, and buffer usage.

This extension evaluates a second question:

Can ACBP expose invalid feature-state regions that Live SQL can compute over but does not explicitly label?

## Outputs

The extension produces:

- outputs/dotk_complexity_summary.csv
- outputs/case_type_validity_summary.csv
- outputs/rule_violation_summary.csv
- outputs/validity_ml_metrics.csv
- outputs/validity_ml_split_metrics.csv
- outputs/validity_ml_uncertainty_summary.csv
- outputs/validity_ml_leave_invalid_type_out.csv
- outputs/ml_key_findings.md

Plots are written to:

- plots/dotk_bits.png
- plots/dotk_support_counts.png
- plots/validity_ml_uncertainty_metrics.png

## Reproduce

Run from repo root:

    python .\11_validity_stress_extension\scripts\run_validity_stress_pipeline.py --host 127.0.0.1 --port 55432 --db acbp_db --user acbp --password acbp

## ML diagnostic

The ML task is not a clinical prediction model.

The target is:

- target_acbp_valid

This is a deterministic ACBP validity label. The classifier tests whether invalid feature-state regions are separable from the same flag/category surface.

The current diagnostic uses:

- 30 repeated stratified splits
- RandomForestClassifier
- accuracy
- valid/invalid F1
- invalid recall
- ROC-AUC
- Brier score
- expected calibration error
- leave-invalid-type-out stress check

## Current key result

DotK state support:

- Observed distinct states: 667
- ACBP-valid states: 391
- ACBP-invalid states: 276
- Invalid support: 41.38%

Uncertainty-aware ML diagnostic:

- Live-blind invalid recall: 0.0000
- ACBP-labeled invalid recall: 0.9989 [0.9980, 0.9998]

## Assumptions

- Synthetic inpatient data.
- Deterministic ACBP validity rules.
- Isolated extension schema.
- Single-node PostgreSQL Docker setup.
- Results are intended to evaluate validity detection and complexity decomposition, not real-world clinical error frequency.

## ML hyperparameters and split settings

The uncertainty-aware validity diagnostic uses the following settings:

Split design:

- Repeated stratified shuffle split
- Number of splits: 30
- Test size: 0.30
- Random seed: 42

Preprocessing:

- Categorical features: one-hot encoded with `handle_unknown="ignore"`
- Numeric features: passed through directly
- Missing length-of-stay value: filled with `-1`
- Location identifiers are treated as categorical strings

Classifier:

- `RandomForestClassifier`
- `n_estimators=300`
- `random_state=42`
- `class_weight="balanced"`
- `min_samples_leaf=2`
- `bootstrap=True`

Reported metrics:

- accuracy
- valid F1
- invalid F1
- invalid precision
- invalid recall
- ROC-AUC
- Brier score
- log loss
- 10-bin expected calibration error
- approximate 95% confidence intervals across repeated splits

Additional stress test:

- leave-invalid-type-out diagnostic
- output file: `outputs/validity_ml_leave_invalid_type_out.csv`

No pretrained model is required or stored. The classifier is trained during the reproducibility run.
