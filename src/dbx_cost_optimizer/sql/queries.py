"""System Tables query templates.

Each template carries a `-- query: <name>` marker (used by MockConnector routing
and as the fact-table key). Placeholders: {lookback}, {util_lookback}.
`pricing.default` = list price; replace with your contracted rate table if you
have a commit/discount.
"""
from __future__ import annotations

_PRICE_JOIN = """
JOIN system.billing.list_prices p
  ON u.sku_name = p.sku_name AND u.usage_unit = p.usage_unit
 AND u.usage_end_time >= p.price_start_time
 AND (p.price_end_time IS NULL OR u.usage_end_time < p.price_end_time)
"""

QUERIES = {
    "spend_by_sku": f"""
-- query: spend_by_sku
SELECT u.sku_name,
       u.billing_origin_product AS product,
       SUM(u.usage_quantity) AS dbus,
       SUM(u.usage_quantity * p.pricing.default) AS cost_usd
FROM system.billing.usage u
{_PRICE_JOIN}
WHERE u.usage_date >= current_date() - INTERVAL {{lookback}} DAYS
GROUP BY 1,2
ORDER BY cost_usd DESC
""",
    "cost_by_entity": f"""
-- query: cost_by_entity
SELECT u.usage_metadata.cluster_id   AS cluster_id,
       u.usage_metadata.job_id       AS job_id,
       u.usage_metadata.warehouse_id AS warehouse_id,
       u.billing_origin_product      AS product,
       SUM(u.usage_quantity * p.pricing.default) AS cost_usd
FROM system.billing.usage u
{_PRICE_JOIN}
WHERE u.usage_date >= current_date() - INTERVAL {{lookback}} DAYS
GROUP BY 1,2,3,4
ORDER BY cost_usd DESC
LIMIT 200
""",
    "idle_clusters": """
-- query: idle_clusters
WITH util AS (
  SELECT cluster_id,
         AVG(cpu_user_percent + cpu_system_percent) AS avg_cpu_pct,
         PERCENTILE(cpu_user_percent + cpu_system_percent, 0.95) AS p95_cpu_pct,
         AVG(mem_used_percent) AS avg_mem_pct
  FROM system.compute.node_timeline
  WHERE start_time >= current_timestamp() - INTERVAL {util_lookback} DAYS
  GROUP BY cluster_id
)
SELECT c.cluster_id, c.cluster_name, c.owned_by,
       c.driver_node_type, c.worker_node_type,
       c.min_autoscale_workers, c.max_autoscale_workers,
       c.auto_termination_minutes,
       u.avg_cpu_pct, u.p95_cpu_pct, u.avg_mem_pct
FROM system.compute.clusters c
JOIN util u ON c.cluster_id = u.cluster_id
WHERE c.delete_time IS NULL
ORDER BY u.avg_cpu_pct ASC
""",
    "weak_autoterminate": """
-- query: weak_autoterminate
SELECT cluster_id, cluster_name, owned_by, auto_termination_minutes, cluster_source
FROM system.compute.clusters
WHERE delete_time IS NULL
  AND cluster_source = 'UI'
  AND (auto_termination_minutes IS NULL OR auto_termination_minutes > 60)
ORDER BY auto_termination_minutes DESC NULLS FIRST
""",
    "allpurpose_running_jobs": f"""
-- query: allpurpose_running_jobs
SELECT jt.job_id, jt.cluster_id, c.cluster_source,
       SUM(u.usage_quantity * p.pricing.default) AS cost_usd
FROM system.lakeflow.job_task_run_timeline jt
JOIN system.compute.clusters c ON jt.cluster_id = c.cluster_id
JOIN system.billing.usage u ON u.usage_metadata.cluster_id = jt.cluster_id
{_PRICE_JOIN}
WHERE c.cluster_source = 'UI'
  AND jt.period_start_time >= current_date() - INTERVAL {{lookback}} DAYS
GROUP BY 1,2,3
ORDER BY cost_usd DESC
""",
    "expensive_jobs": f"""
-- query: expensive_jobs
SELECT jrt.job_id,
       COUNT(*) AS run_count,
       AVG(jrt.period_end_time::double - jrt.period_start_time::double) AS avg_dur_s,
       PERCENTILE(jrt.period_end_time::double - jrt.period_start_time::double, 0.95) AS p95_dur_s,
       SUM(u.usage_quantity * p.pricing.default) AS cost_usd
FROM system.lakeflow.job_run_timeline jrt
JOIN system.billing.usage u ON u.usage_metadata.job_id = jrt.job_id
{_PRICE_JOIN}
WHERE jrt.period_start_time >= current_date() - INTERVAL {{lookback}} DAYS
GROUP BY jrt.job_id
ORDER BY cost_usd DESC
LIMIT 50
""",
    "failed_runs": """
-- query: failed_runs
SELECT job_id, result_state, termination_code, COUNT(*) AS runs
FROM system.lakeflow.job_run_timeline
WHERE period_start_time >= current_date() - INTERVAL {lookback} DAYS
  AND result_state IN ('FAILED','TIMEDOUT','CANCELED')
GROUP BY job_id, result_state, termination_code
ORDER BY runs DESC
""",
    "slow_queries": """
-- query: slow_queries
SELECT statement_id, compute.warehouse_id AS warehouse_id, executed_by,
       total_duration_ms, read_bytes, spilled_local_bytes, produced_rows, read_files
FROM system.query.history
WHERE start_time >= current_timestamp() - INTERVAL 7 DAYS
  AND (spilled_local_bytes > 0 OR total_duration_ms > 60000)
ORDER BY total_duration_ms DESC
LIMIT 100
""",
    "repeated_queries": """
-- query: repeated_queries
SELECT statement_text, COUNT(*) AS exec_count,
       AVG(total_duration_ms) AS avg_ms, SUM(total_duration_ms) AS total_ms
FROM system.query.history
WHERE start_time >= current_timestamp() - INTERVAL 7 DAYS
  AND statement_type = 'SELECT'
GROUP BY statement_text
HAVING COUNT(*) > 10
ORDER BY total_ms DESC
LIMIT 50
""",
    "daily_trend": f"""
-- query: daily_trend
SELECT u.usage_date, SUM(u.usage_quantity * p.pricing.default) AS cost_usd
FROM system.billing.usage u
{_PRICE_JOIN}
WHERE u.usage_date >= current_date() - INTERVAL 90 DAYS
GROUP BY u.usage_date
ORDER BY u.usage_date
""",
}


def render(name: str, lookback: int, util_lookback: int) -> str:
    return QUERIES[name].format(lookback=lookback, util_lookback=util_lookback)
