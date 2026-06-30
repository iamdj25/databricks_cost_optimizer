"""Storage / Delta Agent — tier 1.

Note: file-level stats (small files, version bloat) are NOT in system tables.
In production this agent runs DESCRIBE DETAIL / DESCRIBE HISTORY per table via
the connector. Here it derives candidates from scan-heavy query evidence so the
pipeline stays runnable end-to-end.
"""
from __future__ import annotations

from typing import List

from ..models import Finding
from ..registry import register_agent
from .base import BaseAgent


@register_agent
class StorageAgent(BaseAgent):
    name = "storage"
    requires = ["slow_queries"]
    tier = 1

    def run(self, ctx) -> List[Finding]:
        findings: List[Finding] = []
        seen = set()
        for q in ctx.get_facts("slow_queries"):
            wh = str(q.get("warehouse_id"))
            read_files = int(q.get("read_files") or 0)
            if read_files > 10000 and wh not in seen:
                seen.add(wh)
                findings.append(Finding(
                    agent=self.name, category="needs_optimize", target_type="table",
                    target_id=f"(tables scanned by warehouse {wh})",
                    recommendation="High file count on scanned tables — schedule OPTIMIZE + enable predictive optimization / liquid clustering.",
                    monthly_savings_usd=0.0,  # quantify after DESCRIBE DETAIL in prod
                    effort="M", risk="Low", confidence=0.5,
                    evidence={"read_files": read_files, "source": "slow_queries"},
                    exact_change="OPTIMIZE <table>; ALTER TABLE <table> CLUSTER BY (<cols>);",
                    rollback="n/a (idempotent).",
                ))
        # version bloat placeholder rule (needs DESCRIBE HISTORY in prod)
        return findings
