---
skill: query_tuning
agent: job_query
fix_family: Query tuning
categories: [query_spill, repeated_query]
---
# Query tuning

## When to use
SQL warehouse queries spill, run long, or recompute the same result repeatedly.

## Signals
- `spilled_local_bytes > 1GB` → memory pressure / shuffle skew.
- `total_duration_ms > 60000` on selective queries → bad data skipping.
- Identical `statement_text` run >10x with high cumulative time.

## Fix
- Enable AQE skew handling / partition coalescing.
- Right-size the warehouse (shorter runs can cost less).
- Replace repeated heavy SELECTs with a materialized view / result cache.

## Docs
- https://docs.databricks.com/aws/en/optimizations/aqe
- https://docs.databricks.com/aws/en/views/materialized
