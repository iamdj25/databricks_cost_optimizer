from .base import Connector
from .mock import MockConnector


def build_connector(settings, mock: bool = False) -> Connector:
    """Factory: mock if requested or if Databricks not configured."""
    if mock or not settings.databricks.is_configured:
        return MockConnector()
    from .databricks_sql import DatabricksSQLConnector

    return DatabricksSQLConnector(settings.databricks)


__all__ = ["Connector", "MockConnector", "build_connector"]
