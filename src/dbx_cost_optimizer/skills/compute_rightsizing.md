---
skill: compute_rightsizing
agent: compute
fix_family: Compute right-sizing
categories: [cluster_lower_max_workers, cluster_downsize, no_autoterminate, wrong_cluster_type]
---
# Compute right-sizing

## When to use
Cluster spend is high relative to actual CPU/memory used.

## Signals
- `avg_cpu_pct < 15` over ≥14 days → chronically idle.
- `p95_cpu_pct < 40` and `avg_mem_pct < 50` → over-provisioned node.
- `auto_termination_minutes` null/>60 on interactive cluster.
- all-purpose cluster (`cluster_source = 'UI'`) running scheduled jobs.

## Fix
- Lower autoscale max, set floor to 1.
- Step worker node type down one tier.
- Set auto-termination to ~30 min.
- Move scheduled jobs to ephemeral jobs compute (cheaper DBU rate).

## Guardrails
- Never set spot on clusters tagged `sla=prod`.
- Confidence high only with ≥14 days utilization.

## Docs
https://docs.databricks.com/aws/en/compute/cluster-config-best-practices
