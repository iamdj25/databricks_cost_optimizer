"""Compute / Cluster Optimizer Agent — tier 1."""
from __future__ import annotations

import json
from typing import Dict, List

from ..models import Finding
from ..registry import register_agent
from ..tools.rightsizing import RightSizer
from ..tools.savings import savings_from_cost_fraction
from .base import BaseAgent


@register_agent
class ComputeAgent(BaseAgent):
    name = "compute"
    requires = ["idle_clusters", "cost_by_entity"]
    tier = 1

    def __init__(self, settings, connector) -> None:
        super().__init__(settings, connector)
        self.sizer = RightSizer()

    def _cluster_cost(self, ctx) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for r in ctx.get_facts("cost_by_entity"):
            cid = r.get("cluster_id")
            if cid:
                out[cid] = out.get(cid, 0.0) + float(r.get("cost_usd") or 0.0)
        return out

    def run(self, ctx) -> List[Finding]:
        findings: List[Finding] = []
        costs = self._cluster_cost(ctx)
        weak_at = {r["cluster_id"] for r in ctx.get_facts("weak_autoterminate")}
        enough_data = self.settings.util_lookback_days >= 14

        for c in ctx.get_facts("idle_clusters"):
            cid = c["cluster_id"]
            cost = costs.get(cid, 0.0)

            # right-sizing
            rs = self.sizer.evaluate(c)
            if rs:
                saving = savings_from_cost_fraction(cost, rs.reducible_fraction)
                findings.append(Finding(
                    agent=self.name,
                    category=f"cluster_{rs.action}",
                    target_type="cluster",
                    target_id=cid,
                    recommendation=f"{rs.action.replace('_', ' ')} cluster '{c.get('cluster_name')}' — {rs.rationale}",
                    monthly_savings_usd=saving,
                    effort="S" if rs.action == "lower_max_workers" else "M",
                    risk="Low",
                    confidence=0.8 if enough_data else 0.5,
                    evidence={"avg_cpu_pct": c.get("avg_cpu_pct"), "p95_cpu_pct": c.get("p95_cpu_pct"),
                              "avg_mem_pct": c.get("avg_mem_pct"), "monthly_cost_usd": cost},
                    exact_change=json.dumps({"cluster_id": cid, **rs.target_config}),
                    rollback="Restore previous min/max_workers + node_type from cluster config history.",
                ))

            # missing auto-terminate
            if cid in weak_at:
                saving = savings_from_cost_fraction(cost, 0.15)
                findings.append(Finding(
                    agent=self.name,
                    category="no_autoterminate",
                    target_type="cluster",
                    target_id=cid,
                    recommendation=f"Set auto-termination on '{c.get('cluster_name')}' (currently {c.get('auto_termination_minutes')}).",
                    monthly_savings_usd=saving,
                    effort="S",
                    risk="Low",
                    confidence=0.7,
                    evidence={"auto_termination_minutes": c.get("auto_termination_minutes")},
                    exact_change=json.dumps({"cluster_id": cid, "autotermination_minutes": 30}),
                    rollback="Set autotermination_minutes back to prior value (or null).",
                ))

        # all-purpose cluster running scheduled jobs -> move to jobs compute
        for j in ctx.get_facts("allpurpose_running_jobs"):
            cost = float(j.get("cost_usd") or 0.0)
            saving = savings_from_cost_fraction(cost, 0.40)  # jobs DBU cheaper than all-purpose
            findings.append(Finding(
                agent=self.name,
                category="wrong_cluster_type",
                target_type="job",
                target_id=str(j.get("job_id")),
                recommendation=f"Job {j.get('job_id')} runs on all-purpose cluster {j.get('cluster_id')} — move to jobs compute.",
                monthly_savings_usd=saving,
                effort="M",
                risk="Low",
                confidence=0.75,
                evidence={"cluster_source": j.get("cluster_source"), "monthly_cost_usd": cost},
                exact_change="Set job cluster to new_cluster (jobs compute) instead of existing_cluster_id.",
                rollback="Repoint job back to the interactive cluster.",
            ))
        return findings
