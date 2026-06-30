"""Importing this package registers all built-in agents.

Add your own: create a module, subclass BaseAgent, decorate @register_agent,
import it here (or anywhere before Orchestrator.run).
"""
from .base import BaseAgent
from . import (telemetry, compute, job_query, storage, forecast, report,  # noqa: F401
               pdf_report, alert)

__all__ = ["BaseAgent"]
