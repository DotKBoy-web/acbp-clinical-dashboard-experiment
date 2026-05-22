# Live Query Model Notes

This is the baseline execution model using runtime SQL.

--------------------------------------------------

## Characteristics

- Computes flags at runtime
- Performs multiple joins
- Uses DISTINCT(room, bed)
- Recomputes metrics per query

--------------------------------------------------

## Performance

- ~5.65 ms execution
- ~1214 shared buffer hits
- Higher variability

--------------------------------------------------

## Role

Used as baseline for comparison with ACBP.

--------------------------------------------------

## Limitation

High cost due to repeated computation at runtime.