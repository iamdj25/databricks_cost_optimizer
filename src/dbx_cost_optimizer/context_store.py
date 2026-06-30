"""Shared context store: single source of truth across agents.

Holds normalized facts (from telemetry) + findings (from analysis agents) +
alert events. In-memory with optional JSON persistence. Swap for Delta/SQLite
by subclassing.
"""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Dict, List

from .models import AlertEvent, Finding


class ContextStore:
    def __init__(self) -> None:
        # fact_table_name -> list[dict rows]
        self._facts: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._findings: List[Finding] = []
        self._alerts: List[AlertEvent] = []
        self.meta: Dict[str, Any] = {}

    # ---- facts ----
    def set_facts(self, name: str, rows: List[Dict[str, Any]]) -> None:
        """Idempotent: overwrites the named fact set."""
        self._facts[name] = list(rows)

    def get_facts(self, name: str) -> List[Dict[str, Any]]:
        return self._facts.get(name, [])

    def has_facts(self, name: str) -> bool:
        return bool(self._facts.get(name))

    # ---- findings ----
    def add_findings(self, findings: List[Finding]) -> None:
        self._findings.extend(findings)

    def get_findings(self) -> List[Finding]:
        return list(self._findings)

    def total_identified_savings(self) -> float:
        return round(sum(f.monthly_savings_usd for f in self._findings), 2)

    # ---- alerts ----
    def add_alert(self, event: AlertEvent) -> None:
        self._alerts.append(event)

    def get_alerts(self) -> List[AlertEvent]:
        return list(self._alerts)

    # ---- persistence ----
    def dump(self, path: str) -> None:
        payload = {
            "facts": self._facts,
            "findings": [f.to_dict() for f in self._findings],
            "alerts": [a.to_dict() for a in self._alerts],
            "meta": self.meta,
        }
        with open(path, "w") as fh:
            json.dump(payload, fh, indent=2, default=str)
