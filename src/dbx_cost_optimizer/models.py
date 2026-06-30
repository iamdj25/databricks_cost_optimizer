"""Core data models shared across agents."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional

EFFORT_WEIGHT = {"S": 1.0, "M": 3.0, "L": 8.0}


@dataclass
class Finding:
    """One actionable cost recommendation. Numbers come from tools, not prose."""

    agent: str
    category: str                       # e.g. "idle_cluster", "small_files"
    target_type: str                    # cluster | job | warehouse | table
    target_id: str
    recommendation: str
    monthly_savings_usd: float = 0.0
    effort: str = "M"                   # S | M | L
    risk: str = "Low"                   # Low | Med | High
    confidence: float = 0.5             # 0..1
    evidence: Dict[str, Any] = field(default_factory=dict)
    exact_change: str = ""              # cluster JSON / SQL / job config
    rollback: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    @property
    def priority(self) -> float:
        """Ranking score: savings * confidence / effort_weight."""
        return (self.monthly_savings_usd * self.confidence) / EFFORT_WEIGHT.get(self.effort, 3.0)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["priority"] = round(self.priority, 2)
        return d


@dataclass
class AlertEvent:
    """Emitted when a threshold is breached."""

    rule: str
    severity: str          # info | warning | critical
    message: str
    value_usd: float
    threshold_usd: float
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
