"""Cluster right-sizing heuristics. Returns a target config + reducible fraction.

Deterministic, conservative. Tune thresholds via constructor for your fleet.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class RightSizeResult:
    action: str                 # downsize | lower_max_workers | enable_autoterminate | none
    reducible_fraction: float   # 0..1 of current cost expected to vanish
    target_config: Dict[str, Any]
    rationale: str


class RightSizer:
    def __init__(self, idle_cpu_pct: float = 15.0, oversized_p95_cpu_pct: float = 40.0,
                 oversized_mem_pct: float = 50.0) -> None:
        self.idle_cpu_pct = idle_cpu_pct
        self.oversized_p95_cpu_pct = oversized_p95_cpu_pct
        self.oversized_mem_pct = oversized_mem_pct

    def evaluate(self, cluster: Dict[str, Any]) -> Optional[RightSizeResult]:
        avg_cpu = cluster.get("avg_cpu_pct")
        p95_cpu = cluster.get("p95_cpu_pct")
        avg_mem = cluster.get("avg_mem_pct")
        max_w = cluster.get("max_autoscale_workers") or 0
        min_w = cluster.get("min_autoscale_workers") or 0

        # idle: barely any CPU -> halve the autoscale ceiling, drop floor to 1
        if avg_cpu is not None and avg_cpu < self.idle_cpu_pct:
            new_max = max(1, max_w // 2)
            return RightSizeResult(
                action="lower_max_workers",
                reducible_fraction=0.45,
                target_config={"min_workers": 1, "max_workers": new_max},
                rationale=f"avg_cpu {avg_cpu:.1f}% < {self.idle_cpu_pct}% — chronically idle",
            )

        # oversized: low p95 cpu AND low mem -> step down one node tier (~40% fewer DBU)
        if (p95_cpu is not None and avg_mem is not None
                and p95_cpu < self.oversized_p95_cpu_pct and avg_mem < self.oversized_mem_pct):
            return RightSizeResult(
                action="downsize",
                reducible_fraction=0.30,
                target_config={"note": "step worker_node_type down one size tier",
                               "min_workers": max(1, min_w), "max_workers": max_w},
                rationale=f"p95_cpu {p95_cpu:.1f}% & mem {avg_mem:.1f}% — over-provisioned",
            )
        return None
