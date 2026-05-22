# Artifact Evaluation Guide (ICDM 2026)

This document describes how to evaluate the ACBP Clinical Dashboard Experiment artifact.

--------------------------------------------------

## 1. Scope

The artifact demonstrates:

- ACBP compiled execution model  
- Live SQL baseline comparison  
- Measurable latency and memory improvements  
- Exact semantic equivalence  

--------------------------------------------------

## 2. Evaluation Objectives

Reviewers should verify:

1. Correctness  
   Outputs match exactly between models  

2. Performance  
   Reduced latency and buffer usage  

3. Reproducibility  
   Deterministic results  

4. Model Alignment  
   Implementation matches ACBP theory  

--------------------------------------------------

## 3. Environment Requirements

- PostgreSQL database  
- Synthetic dataset  
- Execution scripts (provided)  

--------------------------------------------------

## 4. Reproduction Steps

1. Load synthetic inpatient dataset  

2. Execute ACBP compilation:
   cbp_materialization.sql  

3. Refresh materialized views:
   SELECT cbp.refresh_fac01_all(true);  

4. Run baseline query:
   SELECT * FROM live_dashboard_query;  

5. Run ACBP query:
   SELECT * FROM cbp.fac01_dashboard_kpis;  

6. Execute benchmark harness  

--------------------------------------------------

## 5. Expected Results

Latency:

- Live SQL ≈ 5.65 ms  
- ACBP ≈ 1.91 ms  

Buffer Usage:

- Live SQL ≈ 1214 shared hits  
- ACBP ≈ 98 shared hits  

Correctness:

- Outputs identical (hash match)  

--------------------------------------------------

## 6. Evaluation Dimensions

### Correctness

- Compare query outputs  
- Verify exact matching  

### Performance

- Measure execution time  
- Measure buffer usage  

### Stability

- Repeat runs  
- Confirm low variance  

### Structural Behavior

- Verify no runtime recomputation  
- Confirm use of materialized state  

--------------------------------------------------

## 7. Interpretation

Performance gains arise because:

- Computation is shifted to compile-time  
- State space is precomputed  
- Query execution is simplified  

--------------------------------------------------

## 8. Comparison to BI Systems

Traditional Systems:

- SQL: runtime computation  
- Web Intelligence: semantic abstraction  
- Power BI: optimized evaluation  

ACBP:

- precomputes decision space  
- eliminates repeated computation  
- ensures deterministic execution  

--------------------------------------------------

## 9. Limitations

- Synthetic dataset  
- Single-node evaluation  
- Dependent on category size  

--------------------------------------------------

## 10. Verification Checklist

The artifact is valid if:

- Queries execute successfully  
- Results match exactly  
- Performance differences are observable  
- Model aligns with ACBP definitions  

--------------------------------------------------

## 11. Conclusion

The artifact demonstrates that ACBP transforms query execution by replacing runtime computation with pre-materialized decision spaces, resulting in measurable performance improvements.