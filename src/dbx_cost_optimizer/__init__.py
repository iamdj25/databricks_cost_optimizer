"""Multi-agent Databricks cost optimizer.

Public API:
    from dbx_cost_optimizer import Orchestrator, Settings, ContextStore
"""
from .config import Settings
from .context_store import ContextStore
from .orchestrator import Orchestrator
from .models import Finding
from .registry import register_agent, get_agent, list_agents

__version__ = "0.1.0"

__all__ = [
    "Settings",
    "ContextStore",
    "Orchestrator",
    "Finding",
    "register_agent",
    "get_agent",
    "list_agents",
]
