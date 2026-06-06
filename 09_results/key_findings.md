# Key Findings

## ✅ 1. Correctness
- CBP produces identical results to Live SQL queries.
- Verified using `result_hash` across paired iterations.
- Observed **100% equivalence** in evaluated samples (no mismatches in buffer-sampled iterations).

---

## ✅ 2. Performance (Latency)
- CBP consistently outperforms Live queries.
- Observed speedup (Live / CBP):
  - Range: **1.68× – 2.23×**
  - Mean (buffer-sampled points): **~1.93×**
- Example:
  - Iteration 20: Live = 409.05 ms, CBP = 183.23 ms

✅ Interpretation:
> CBP reduces dashboard latency by approximately **2× under dynamic workload conditions**.

---

## ✅ 3. Mechanism (Buffer Usage)
- Shared buffer hits (EXPLAIN BUFFERS):
  - Live: ~10,600 – 10,745
  - CBP: ~1,221 – 1,241

- Observed:
  - Buffer ratio (Live / CBP): **8.61× – 8.74×**
  - Average: **~8.68×**
  - Reduction: **~88.5% fewer buffer hits**

✅ Interpretation:
> CBP drastically reduces memory page access, eliminating expensive joins and aggregations at runtime.

---

## ✅ 4. Stability
- Feed cycle latency:
  - ~16 seconds per iteration
  - Very low variance (stable workload generator)

- Query latency:
  - Stable across iterations (low variability)

✅ Interpretation:
> Performance improvements are consistent, not due to noise.

---

## ✅ 5. Observed Failures
- Iteration 5: CBP timeout
- Iteration 38: Live timeout

- Both recorded explicitly in logs (`ok = 0`)

✅ Interpretation:
> Failures are rare and explicitly tracked; excluded from aggregated statistics.

---

# ✅ Final Conclusion

CBP demonstrates:

- ✅ **Semantic equivalence** (correctness preserved)
- ✅ **~2× latency improvement**
- ✅ **~8.7× reduction in buffer usage**
- ✅ **Stable performance under dynamic workload**

> These results confirm that CBP improves performance by reducing runtime computation and memory access, not by approximating results.
```
---

## ✅ 7. Uncertainty-Aware Validity ML Diagnostic

The validity-stress ML diagnostic was rerun using **30 repeated stratified splits** to avoid relying on a single train/test split.

Live-blind baseline:

- Accuracy: **0.9062**
- Invalid F1: **0.0000**
- Invalid recall: **0.0000**
- ROC-AUC: **0.5000**
- Brier score: **0.0938**
- ECE: **0.0938**

ACBP-labeled validity classifier:

- Accuracy: **0.9994** [0.9991, 0.9998]
- Invalid F1: **0.9970** [0.9951, 0.9990]
- Invalid recall: **0.9989** [0.9980, 0.9998]
- ROC-AUC: **1.0000**
- Brier score: **0.0101** [0.0098, 0.0103]
- ECE: **0.0620** [0.0611, 0.0629]

✅ Interpretation:

> The ML diagnostic is not a clinical prediction model. It tests whether the deterministic ACBP validity boundary is separable from the flag/category surface. The Live-blind baseline achieves high apparent accuracy only because most rows are valid, but it has zero invalid recall. ACBP makes invalid-state detection explicit.
