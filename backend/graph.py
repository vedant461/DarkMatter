from __future__ import annotations

import logging
from typing import Any

from falkordb import FalkorDB

from .config import settings

log = logging.getLogger(__name__)


class GraphStore:
    def __init__(self) -> None:
        self.db = FalkorDB(host=settings.falkordb_host, port=settings.falkordb_port)
        self.graph = self.db.select_graph(settings.falkordb_graph)

    def query(self, cypher: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        result = self.graph.query(cypher, params or {})
        headers = [str(header) for header in result.header]
        return [dict(zip(headers, row)) for row in result.result_set]

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
