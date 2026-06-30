"""Sink Agent — writes findings + usage to Delta tables via the SQL warehouse.

Downstream Genie + dashboard read these tables. Runs only with a live connector
(skipped in mock). Idempotent: recreates the findings snapshot each run.
"""
from __future__ import annotations

from typing import List

from ..connectors.mock import MockConnector
from ..models import Finding
from ..registry import register_agent
from .base import BaseAgent


def _sql_str(v) -> str:
    if v is None:
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"


@register_agent
class SinkAgent(BaseAgent):
    name = "sink"
    requires: List[str] = []
    tier = 2

    def run(self, ctx) -> List[Finding]:
        if isinstance(self.connector, MockConnector):
            ctx.meta["sink_note"] = "skipped (mock connector)"
            return []

        db = self.settings.databricks
        findings_tbl = db.findings_table
        usage_tbl = db.usage_table

        self.connector.query(f"CREATE SCHEMA IF NOT EXISTS {db.catalog}.{db.schema}")
        self.connector.query(f"""
            CREATE TABLE IF NOT EXISTS {findings_tbl} (
                id STRING, agent STRING, category STRING, fix_family STRING,
                target_type STRING, target_id STRING, recommendation STRING,
                monthly_savings_usd DOUBLE, effort STRING, risk STRING,
                confidence DOUBLE, priority DOUBLE, exact_change STRING,
                rollback STRING, doc_url STRING, generated_at TIMESTAMP
            ) USING DELTA
        """)
        # snapshot replace
        self.connector.query(f"TRUNCATE TABLE {findings_tbl}")

        from ..docs_catalog import lookup
        rows = []
        for f in ctx.get_findings():
            doc = lookup(f.category)
            rows.append(
                "(" + ", ".join([
                    _sql_str(f.id), _sql_str(f.agent), _sql_str(f.category),
                    _sql_str(doc.fix_family), _sql_str(f.target_type), _sql_str(f.target_id),
                    _sql_str(f.recommendation), str(f.monthly_savings_usd), _sql_str(f.effort),
                    _sql_str(f.risk), str(f.confidence), str(round(f.priority, 2)),
                    _sql_str(f.exact_change), _sql_str(f.rollback), _sql_str(doc.url),
                    "current_timestamp()",
                ]) + ")"
            )
        if rows:
            # chunk to keep statements reasonable
            for i in range(0, len(rows), 200):
                values = ", ".join(rows[i:i + 200])
                self.connector.query(f"INSERT INTO {findings_tbl} VALUES {values}")

        # usage daily for the spend dashboard tile
        self.connector.query(f"""
            CREATE TABLE IF NOT EXISTS {usage_tbl} (
                usage_date STRING, cost_usd DOUBLE
            ) USING DELTA
        """)
        self.connector.query(f"TRUNCATE TABLE {usage_tbl}")
        urows = [f"({_sql_str(r.get('usage_date'))}, {float(r.get('cost_usd') or 0)})"
                 for r in ctx.get_facts("daily_trend")]
        if urows:
            self.connector.query(f"INSERT INTO {usage_tbl} VALUES {', '.join(urows)}")

        ctx.meta["sink_findings_table"] = findings_tbl
        ctx.meta["sink_usage_table"] = usage_tbl
        ctx.meta["sink_rows"] = len(rows)
        return []
