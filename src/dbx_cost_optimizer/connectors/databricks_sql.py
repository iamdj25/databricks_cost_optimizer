"""Real connector via databricks-sql-connector (System Tables live here)."""
from __future__ import annotations

from typing import Any, Dict, List

from ..config import DatabricksConfig
from .base import Connector


class DatabricksSQLConnector(Connector):
    def __init__(self, cfg: DatabricksConfig) -> None:
        if not cfg.is_configured:
            raise ValueError("Databricks config incomplete (host/http_path/token).")
        self._cfg = cfg
        self._conn = None

    def _connect(self):
        if self._conn is not None:
            return self._conn
        try:
            from databricks import sql  # lazy import; optional dependency
        except ImportError as e:
            raise ImportError(
                "databricks-sql-connector not installed. "
                "Install extra: pip install 'dbx-cost-optimizer[databricks]'"
            ) from e
        self._conn = sql.connect(
            server_hostname=self._cfg.server_hostname,
            http_path=self._cfg.http_path,
            access_token=self._cfg.access_token,
        )
        return self._conn

    def query(self, sql: str) -> List[Dict[str, Any]]:
        conn = self._connect()
        with conn.cursor() as cur:
            cur.execute(sql)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
