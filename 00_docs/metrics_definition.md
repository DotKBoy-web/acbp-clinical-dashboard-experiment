# Metrics Definition

This document defines all evaluation metrics used in the experiment.

--------------------------------------------------

## 1. Latency

Definition:

Total execution time of query in milliseconds.

Measurement:

- Captured using PostgreSQL execution timing
- Includes planning + execution

--------------------------------------------------

## 2. Shared Buffer Hits

Definition:

Number of shared memory page accesses during query execution.

Interpretation:

- High values indicate more memory access
- Lower values indicate more efficient execution

--------------------------------------------------

## 3. Speedup

Definition:

Speedup = Live SQL latency / ACBP latency

Interpretation:

- Values > 1 indicate improvement
- Represents relative performance gain

--------------------------------------------------

## 4. Buffer Reduction

Definition:

Buffer Reduction = (1 - ACBP / Live SQL) × 100%

Interpretation:

- Measures reduction in memory usage
- Indicates elimination of redundant computation

--------------------------------------------------

## 5. Correctness

Definition:

Equality of outputs across execution models.

Measurement:

- Hash comparison of result sets
- Row-by-row verification

--------------------------------------------------

## 6. Stability

Definition:

Variance in execution time across runs.

Interpretation:

- Lower variance indicates predictable execution
- ACBP expected to have lower variance

--------------------------------------------------

## Key Insight

Latency improvement in ACBP is correlated with reduction in buffer usage, indicating less runtime computation.