"""Agent registry — the extensibility seam.

Add a new agent by subclassing BaseAgent and decorating with @register_agent.
The orchestrator discovers agents by name; no core edits needed.
"""
from __future__ import annotations

from typing import Dict, List, Type

_REGISTRY: Dict[str, Type] = {}


def register_agent(cls=None):
    """Class decorator. Uses cls.name as the registry key."""

    def _wrap(c):
        key = getattr(c, "name", None)
        if not key:
            raise ValueError(f"{c.__name__} must define a class attribute `name`")
        _REGISTRY[key] = c
        return c

    return _wrap(cls) if cls is not None else _wrap


def get_agent(name: str) -> Type:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown agent '{name}'. Registered: {list_agents()}")
    return _REGISTRY[name]


def list_agents() -> List[str]:
    return sorted(_REGISTRY)
