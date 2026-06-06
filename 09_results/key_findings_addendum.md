## Validity-Stress / DotK Extension

A secondary validity-stress extension was added using the same benchmark database and an isolated `validity_ext` schema. The source `cerner`, `cerner_ref`, and `cbp` schemas were not modified.

The extension produced:

- Observed distinct states: **667**
- ACBP-valid distinct states: **391**
- ACBP-invalid distinct states: **276**
- Invalid support percentage: **41.38%**

DotK complexity decomposition:

- \(K_{\text{obs}}\): **9.3815 bits**
- \(K_{\text{valid}}\): **8.6110 bits**
- \(K_{\text{invalid}}\): **8.1085 bits**
- \(K_{\Delta}\): **0.7705 bits**

A validity-detection ML diagnostic was also evaluated. The Live-blind baseline treated all states as valid, achieving high apparent accuracy because most rows were valid, but it had **0.0000 invalid recall**. The ACBP-labeled validity classifier achieved **1.0000 invalid recall** and **1.0000 invalid F1** in the controlled stress setting.

Interpretation: Live SQL computes dashboard metrics but does not label invalid feature-state regions. ACBP provides an explicit validity boundary, enabling DotK-style valid/invalid complexity decomposition and validity-aware downstream diagnostics.
