"""BaseAgent — the contract every agent implements.

Extend the system: subclass, set `name` + `requires`, implement `run`, decorate
with @register_agent. Orchestrator handles ordering and wiring.
"""
from __future__ import annotations

import abc
from typing import List

from ..config import Settings
from ..connectors.base import Connector
from ..context_store import ContextStore
from ..models import Finding


class BaseAgent(abc.ABC):
    #: unique registry key
    name: str = ""
    #: fact tables this agent reads (empty for producers like telemetry)
    requires: List[str] = []
    #: run order tier — lower runs first (0 telemetry, 1 analysis, 2 forecast/alert/report)
    tier: int = 1

    def __init__(self, settings: Settings, connector: Connector) -> None:
        self.settings = settings
        self.connector = connector

    def can_run(self, ctx: ContextStore) -> bool:
        return all(ctx.has_facts(r) for r in self.requires)

    @abc.abstractmethod
    def run(self, ctx: ContextStore) -> List[Finding]:
        """Read ctx, optionally write facts/findings, return new findings."""
