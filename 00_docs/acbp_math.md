# ACBP Mathematical Model

This section formalizes the Al‑Anazi Categorical‑Boolean Paradigm (ACBP) as a deterministic, relational execution model.

--------------------------------------------------

## 1. Core Definitions

Let:

- F ∈ {0,1}^B be an ordered Boolean state vector  
- c ∈ C = Π Ci be a tuple of categorical dimensions  
- R be a finite set of constraints  

Each constraint r ∈ R is a predicate:

r(F, c) ∈ {true, false}

--------------------------------------------------

## 2. ACBP Validity Predicate

ACBP(F, c) = AND over all constraints r ∈ R of r(F, c)

A configuration (F, c) is valid if and only if all constraints hold.

--------------------------------------------------

## 3. Derived Sets

### Decision Space

D = { (F, c) ∈ {0,1}^B × C | ACBP(F, c) = true }

This represents all valid state–context combinations.

--------------------------------------------------

### Valid Mask Space

M = { F | ∃ c ∈ C such that ACBP(F, c) = true }

This represents all Boolean configurations that are valid under at least one context.

--------------------------------------------------

## 4. Projection Constraint

ACBP enforces:

M = π_F(D)

Meaning:

- Valid masks are derived only from valid (F, c) pairs  
- Impossible states are eliminated  

--------------------------------------------------

## 5. Present-Only Decision Space

D_present = D ∩ ({0,1}^B × C')

Where:

- C' = observed category tuples in data  

This reduces computation while preserving correctness.

--------------------------------------------------

## 6. Compilation to SQL

The ACBP model compiles into SQL-native artifacts:

- decision_space → representation of D  
- valid_masks → projection of D  
- validators → equivalent to ACBP(F, c)  
- materialized views → optimized execution structures  

--------------------------------------------------

## 7. Execution Interpretation

Traditional SQL:

- evaluates constraints at runtime  
- recomputes joins and aggregations  

ACBP:

- precomputes valid state space  
- executes queries as joins over materialized structures  

--------------------------------------------------

## 8. Key Property

ACBP preserves correctness while minimizing runtime computation.

It achieves this by moving evaluation from runtime to compile-time.