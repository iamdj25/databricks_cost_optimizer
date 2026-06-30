"""Orchestrator — supervisor that runs agents by tier and aggregates results.

Flow: telemetry (tier 0) -> analysis agents (tier 1) -> forecast+report (tier 2)
-> alert (tier 3). Tier 1 agents are independent; run them concurrently.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

from . import agents as _agents  # noqa: F401  (registers built-ins)
from .config import Settings
from .connectors import build_connector
from .connectors.base import Connector
from .context_store import ContextStore
from .notifications.base import Notifier
from .registry import get_agent, list_agents

# default crew, in dependency order; extend by appending registered agent names
# Analysis + reporting crew. dashboard/genie are workspace-only and run via
# the `publish`/`genie` CLI commands, not this default crew.
DEFAULT_CREW = ["telemetry", "compute", "job_query", "storage", "forecast", "report",
                "pdf_report", "sink", "alert"]


class Orchestrator:
    def __init__(self, settings: Optional[Settings] = None,
                 connector: Optional[Connector] = None,
                 crew: Optional[List[str]] = None,
                 mock: bool = False) -> None:
        self.settings = settings or Settings.load()
        self.connector = connector or build_connector(self.settings, mock=mock)
        self.crew = crew or DEFAULT_CREW
        self.ctx = ContextStore()
        # alert wiring (set before run to inject notifier / disable email)
        self.alert_notifier: Optional[Notifier] = None
        self.alert_dry_run: bool = False
        self.alert_send_email: bool = True
        self.max_workers: int = 6

    def _instantiate(self):
        objs = [get_agent(name)(self.settings, self.connector) for name in self.crew]
        return sorted(objs, key=lambda a: a.tier)

    def _configure_alert(self, agent) -> None:
        if agent.name == "alert":
            agent.notifier = self.alert_notifier
            agent.dry_run = self.alert_dry_run
            agent.send_email = self.alert_send_email

    def run(self) -> ContextStore:
        agents = self._instantiate()
        tiers: Dict[int, list] = {}
        for a in agents:
            tiers.setdefault(a.tier, []).append(a)

        for tier in sorted(tiers):
            batch = tiers[tier]
            runnable = [a for a in batch if a.can_run(self.ctx)]
            for a in batch:
                self._configure_alert(a)

            if tier == 1 and len(runnable) > 1:
                # independent analysis agents -> parallel
                with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
                    results = list(ex.map(lambda a: (a.name, a.run(self.ctx)), runnable))
                for _, findings in results:
                    self.ctx.add_findings(findings)
            else:
                for a in runnable:
                    self.ctx.add_findings(a.run(self.ctx))

            skipped = [a.name for a in batch if a not in runnable]
            if skipped:
                self.ctx.meta.setdefault("skipped_agents", []).extend(skipped)
        return self.ctx

    @staticmethod
    def available_agents() -> List[str]:
        return list_agents()
