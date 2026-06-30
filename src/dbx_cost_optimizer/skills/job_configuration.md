---
skill: job_configuration
agent: job_query
fix_family: Job configuration
categories: [failed_run_waste, batch_eligible, wrong_cluster_type]
---
# Job configuration

## When to use
Jobs waste DBU through failed retries, excessive tiny runs, or wrong compute.

## Signals
- High share of `FAILED/TIMEDOUT/CANCELED` runs.
- >200 runs at <300s avg (startup overhead dominates).
- Scheduled job on all-purpose cluster.

## Fix
- Cap retries; fix root termination cause.
- Switch to file-arrival trigger or coarser schedule (batch).
- Run on ephemeral jobs compute, not interactive.

## Docs
- https://docs.databricks.com/aws/en/jobs/settings
- https://docs.databricks.com/aws/en/jobs/file-arrival-triggers
- https://docs.databricks.com/aws/en/jobs/compute
