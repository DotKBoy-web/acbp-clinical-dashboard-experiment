# Validity ML Key Findings

This extension uses the same benchmark database but creates an isolated `validity_ext` schema.

The source `cerner`, `cerner_ref`, and `cbp` schemas are not modified.


## DotK Complexity

- Observed distinct states: 667
- ACBP-valid distinct states: 391
- ACBP-invalid distinct states: 276
- Invalid support percentage: 41.38%
- K_obs: 9.3815 bits
- K_valid: 8.6110 bits
- K_invalid: 8.1085 bits
- K_gap: 0.7705 bits


## Uncertainty-aware ML Diagnostic

The ML target is `target_acbp_valid`.

This is not a clinical outcome prediction model. It is a validity-detection diagnostic showing whether invalid feature-state spaces are separable from the same flag and category surface.

To avoid reporting a single overfit train/test split, the script now uses 30 repeated stratified splits and reports mean metrics with approximate 95% confidence intervals.

### Live-blind baseline

The Live SQL baseline computes dashboard states but has no explicit validity boundary. Therefore the baseline treats all states as valid.

- Accuracy: 0.9062 [0.9062, 0.9062]
- F1 invalid: 0.0000 [0.0000, 0.0000]
- Invalid recall: 0.0000 [0.0000, 0.0000]
- ROC-AUC: 0.5000 [0.5000, 0.5000]
- Brier score: 0.0938 [0.0938, 0.0938]
- ECE: 0.0938 [0.0938, 0.0938]

### ACBP-labeled validity classifier

The classifier is trained on flags and categories to approximate the deterministic ACBP validity label.

- Accuracy: 0.9994 [0.9991, 0.9998]
- F1 invalid: 0.9970 [0.9951, 0.9990]
- Invalid recall: 0.9989 [0.9980, 0.9998]
- ROC-AUC: 1.0000 [1.0000, 1.0000]
- Brier score: 0.0101 [0.0098, 0.0103]
- ECE: 0.0620 [0.0611, 0.0629]

## Leave-invalid-type-out diagnostic

A secondary stress check holds out each invalidity type from training and tests whether the model detects that unseen invalidity mechanism. Results are saved in:

`validity_ml_leave_invalid_type_out.csv`

## Interpretation

Live SQL can compute dashboard metrics over a feature-state surface, but it does not explicitly label invalid states.

ACBP provides the deterministic validity boundary.

DotK then measures how much of the observed state-space support is valid versus invalid on a log-scale.
