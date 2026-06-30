"""Telemetry Agent — tier 0. Runs System Tables queries, writes normalized facts.

No findings. Producer for everyone downstream.
"""
from __future__ import annotations

from typing import List

from ..models import Finding
from ..registry import register_agent
from ..sql.queries import QUERIES, render
from .base import BaseAgent

# query names this agent materializes into the context store
_FACT_QUERIES = list(QUERIES.keys())


@register_agent
class TelemetryAgent(BaseAgent):
    name = "telemetry"
    requires: List[str] = []
    tier = 0

    def run(self, ctx) -> List[Finding]:
        warnings = []
        for q in _FACT_QUERIES:
            sql = render(q, self.settings.lookback_days, self.settings.util_lookback_days)
            try:
                rows = self.connector.query(sql)
            except Exception as e:  # one bad query must not kill ingestion
                rows = []
                warnings.append(f"{q}: {e}")
            ctx.set_facts(q, rows)
        ctx.meta["telemetry_warnings"] = warnings
        ctx.meta["telemetry_row_counts"] = {q: len(ctx.get_facts(q)) for q in _FACT_QUERIES}
        return []
