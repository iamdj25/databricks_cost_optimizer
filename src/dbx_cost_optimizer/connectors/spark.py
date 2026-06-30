"""Spark connector — runs inside Databricks (job/notebook) using the active
SparkSession. No token needed; uses the running identity's permissions, which is
ideal for a Databricks Asset Bundle job."""
from __future__ import annotations

from typing import Any, Dict, List

from .base import Connector


class SparkConnector(Connector):
    def __init__(self, spark=None) -> None:
        self._spark = spark or self._active_spark()

    @staticmethod
    def _active_spark():
        try:
            from pyspark.sql import SparkSession
        except ImportError as e:
            raise ImportError("pyspark not available — run inside Databricks.") from e
        s = SparkSession.getActiveSession()
        if s is None:
            s = SparkSession.builder.getOrCreate()
        return s

    def query(self, sql: str) -> List[Dict[str, Any]]:
        df = self._spark.sql(sql)
        cols = df.columns
        return [dict(zip(cols, row)) for row in df.collect()]


def in_databricks() -> bool:
    import os

    if os.getenv("DATABRICKS_RUNTIME_VERSION"):
        return True
    try:
        from pyspark.sql import SparkSession

        return SparkSession.getActiveSession() is not None
    except Exception:
        return False
