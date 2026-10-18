from __future__ import annotations

import logging
import time
from typing import Any

from falkordb import FalkorDB
from falkordb.edge import Edge
from falkordb.node import Node

from .config import settings

log = logging.getLogger(__name__)


def _plain(value: Any) -> Any:
    if isinstance(value, (Node, Edge)):
        return dict(value.properties)
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


class GraphStore:
    def __init__(self) -> None:
        self._graph = None

    @property
    def graph(self):
        if self._graph is None:
            self._graph = self._connect()
        return self._graph

    def _connect(self, attempts: int = 30, delay: float = 1.0):
        for n in range(1, attempts + 1):
            try:
                db = FalkorDB(host=settings.falkordb_host, port=settings.falkordb_port)
                return db.select_graph(settings.falkordb_graph)
            except Exception as exc:
                log.warning("FalkorDB not ready (%d/%d): %s", n, attempts, exc)
                time.sleep(delay)
        raise RuntimeError(f"cannot reach FalkorDB at {settings.falkordb_host}:{settings.falkordb_port}")

    def query(self, cypher: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        result = self.graph.query(cypher, params or {})
        headers = [str(h[1]) if isinstance(h, (list, tuple)) else str(h) for h in result.header]
        return [dict(zip(headers, (_plain(v) for v in row))) for row in result.result_set]

    def write(self, cypher: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return self.query(cypher, params)

    def ensure_schema(self) -> None:
        for statement in (
            "CREATE INDEX FOR (n:Author) ON (n.email)",
            "CREATE INDEX FOR (n:Commit) ON (n.sha)",
            "CREATE INDEX FOR (n:File) ON (n.path)",
            "CREATE INDEX FOR (n:Endpoint) ON (n.id)",
        ):
            try:
                self.write(statement)
            except Exception as exc:
                log.debug("schema statement skipped: %s", exc)


store = GraphStore()