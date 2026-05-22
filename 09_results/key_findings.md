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