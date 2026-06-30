"""Databricks WorkspaceClient factory (SDK).

The SDK natively reads ~/.databrickscfg, env vars, and OAuth. We just pass the
profile through. Used by the sink, dashboard, and Genie agents.
"""
from __future__ import annotations

from typing import Optional

from .config import Settings


def get_workspace_client(settings: Settings):
    """Return a databricks.sdk.WorkspaceClient for the configured profile."""
    try:
        from databricks.sdk import WorkspaceClient
    except ImportError as e:
        raise ImportError(
            "databricks-sdk not installed. Install: pip install 'dbx-cost-optimizer[databricks]'"
        ) from e

    profile = settings.databricks.profile
    if profile:
        return WorkspaceClient(profile=profile)
    # falls back to env / DEFAULT profile / OAuth automatically
    if settings.databricks.server_hostname and settings.databricks.access_token:
        return WorkspaceClient(
            host=f"https://{settings.databricks.server_hostname}",
            token=settings.databricks.access_token,
        )
    return WorkspaceClient()


def resolve_warehouse_id(settings: Settings, client=None) -> Optional[str]:
    """Use configured warehouse, else first RUNNING/available SQL warehouse."""
    if settings.databricks.warehouse_id:
        return settings.databricks.warehouse_id
    if client is None:
        return None
    try:
        for wh in client.warehouses.list():
            return wh.id
    except Exception:
        return None
    return None
