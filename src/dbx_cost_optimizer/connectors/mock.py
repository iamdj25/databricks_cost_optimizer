"""Mock connector with canned System-Tables-shaped fixtures.

Lets the whole pipeline run with no Databricks workspace — for demos, tests,
and local development. Routes by the `-- query: <name>` marker each query
template carries (see sql/queries.py).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from .base import Connector

_MARKER = re.compile(r"--\s*query:\s*(\w+)")

FIXTURES: Dict[str, List[Dict[str, Any]]] = {
    "spend_by_sku": [
        {"sku_name": "PREMIUM_ALL_PURPOSE_COMPUTE", "product": "INTERACTIVE", "dbus": 41000, "cost_usd": 22550.0},
        {"sku_name": "PREMIUM_JOBS_COMPUTE", "product": "JOBS", "dbus": 30000, "cost_usd": 9000.0},
        {"sku_name": "PREMIUM_SQL_COMPUTE", "product": "SQL", "dbus": 18000, "cost_usd": 12600.0},
    ],
    "cost_by_entity": [
        {"cluster_id": "0721-aaa", "job_id": None, "warehouse_id": None, "product": "INTERACTIVE", "cost_usd": 8200.0},
        {"cluster_id": "0721-bbb", "job_id": None, "warehouse_id": None, "product": "INTERACTIVE", "cost_usd": 3100.0},
        {"cluster_id": None, "job_id": "J-204", "warehouse_id": None, "product": "JOBS", "cost_usd": 4300.0},
        {"cluster_id": None, "job_id": None, "warehouse_id": "wh-9", "product": "SQL", "cost_usd": 6100.0},
    ],
    "idle_clusters": [
        {"cluster_id": "0721-aaa", "cluster_name": "ds-team-shared", "owned_by": "ana@x.com",
         "driver_node_type": "i3.2xlarge", "worker_node_type": "i3.2xlarge",
         "min_autoscale_workers": 4, "max_autoscale_workers": 12, "auto_termination_minutes": None,
         "avg_cpu_pct": 6.2, "p95_cpu_pct": 22.0, "avg_mem_pct": 30.0},
        {"cluster_id": "0721-bbb", "cluster_name": "etl-oversized", "owned_by": "etl@x.com",
         "driver_node_type": "r5.4xlarge", "worker_node_type": "r5.4xlarge",
         "min_autoscale_workers": 2, "max_autoscale_workers": 8, "auto_termination_minutes": 120,
         "avg_cpu_pct": 28.0, "p95_cpu_pct": 38.0, "avg_mem_pct": 41.0},
    ],
    "weak_autoterminate": [
        {"cluster_id": "0721-aaa", "cluster_name": "ds-team-shared", "owned_by": "ana@x.com",
         "auto_termination_minutes": None, "cluster_source": "UI"},
    ],
    "allpurpose_running_jobs": [
        {"job_id": "J-204", "cluster_id": "0721-bbb", "cluster_source": "UI", "cost_usd": 4300.0},
    ],
    "expensive_jobs": [
        {"job_id": "J-204", "run_count": 720, "avg_dur_s": 180.0, "p95_dur_s": 410.0, "cost_usd": 4300.0},
    ],
    "failed_runs": [
        {"job_id": "J-204", "result_state": "FAILED", "termination_code": "DRIVER_ERROR", "runs": 38},
    ],
    "slow_queries": [
        {"statement_id": "q-1", "warehouse_id": "wh-9", "executed_by": "bi@x.com",
         "total_duration_ms": 142000, "read_bytes": 980000000000, "spilled_local_bytes": 12000000000,
         "produced_rows": 1200, "read_files": 41000},
    ],
    "repeated_queries": [
        {"statement_text": "SELECT * FROM sales.daily WHERE region=?", "exec_count": 240,
         "avg_ms": 5200.0, "total_ms": 1248000.0},
    ],
    "daily_trend": [
        {"usage_date": f"2026-06-{d:02d}", "cost_usd": 1400.0 + d * 12} for d in range(1, 31)
    ],
}


class MockConnector(Connector):
    def query(self, sql: str) -> List[Dict[str, Any]]:
        m = _MARKER.search(sql)
        if not m:
            return []
        return list(FIXTURES.get(m.group(1), []))
