from .base import Connector
from .mock import MockConnector


def build_connector(settings, mock: bool = False) -> Connector:
    """Factory: mock if requested; Spark when inside Databricks; else env/CLI profile."""
    if mock:
        return MockConnector()
    # running inside a Databricks job/notebook -> use the cluster's SparkSession
    from .spark import in_databricks

    if in_databricks():
        from .spark import SparkConnector

        return SparkConnector()
    if not settings.databricks.is_configured:
        # pull host/token from Databricks CLI config (and http_path from warehouse_id)
        settings.databricks.merge_from_cli_profile()
    if not settings.databricks.is_configured:
        return MockConnector()
    from .databricks_sql import DatabricksSQLConnector

    return DatabricksSQLConnector(settings.databricks)


__all__ = ["Connector", "MockConnector", "build_connector"]
