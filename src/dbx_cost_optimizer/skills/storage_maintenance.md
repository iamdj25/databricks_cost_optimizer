---
skill: storage_maintenance
agent: storage
fix_family: Storage maintenance
categories: [small_files_scan, needs_optimize]
---
# Storage maintenance

## When to use
Queries scan huge file counts; tables lack compaction/clustering; old versions pile up.

## Signals
- `read_files` per query in the tens of thousands.
- avg file size < 64 MB.
- No recent OPTIMIZE / no VACUUM (version bloat).

## Fix
- `OPTIMIZE <table>` (compaction).
- `ALTER TABLE <table> CLUSTER BY (<filter_cols>)` (liquid clustering) or Z-ORDER.
- Enable predictive optimization (auto OPTIMIZE/VACUUM).
- `VACUUM` with default 7-day retention (warn on time-travel impact).

## Guardrails
- Never VACUUM below default retention without explicit override + warning.
- Quantify storage $ and downstream scan $ separately.

## Docs
- https://docs.databricks.com/aws/en/delta/optimize
- https://docs.databricks.com/aws/en/optimizations/predictive-optimization
