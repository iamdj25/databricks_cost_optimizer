"""Connector interface. Implement `query` to add a new data source."""
from __future__ import annotations

import abc
from typing import Any, Dict, List


class Connector(abc.ABC):
    @abc.abstractmethod
    def query(self, sql: str) -> List[Dict[str, Any]]:
        """Run SQL, return list of row dicts."""

    def close(self) -> None:  # optional override
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
