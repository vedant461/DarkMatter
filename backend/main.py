from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import settings
from .extract import extract_fastapi
from .graph import store
from .ingest import ingest_repo

app = FastAPI(title="DarkMatter")


class IngestRequest(BaseModel):
    repo: str
    max_commits: int = 300


@app.on_event("startup")
async def startup() -> None:
    store.ensure_schema()


@app.post("/ingest")
def ingest(request: IngestRequest) -> dict[str, object]:
    path = Path(request.repo)
    if not path.exists():
        raise HTTPException(404, "repo path does not exist")
    result = ingest_repo(str(path), request.max_commits)
    result["extraction"] = extract_fastapi(str(path))
    return result


@app.get("/graph")
def graph() -> dict[str, object]:
    rows = store.query("MATCH (n)-[r]->(m) RETURN labels(n)[0] AS source_type, n, type(r) AS relation, labels(m)[0] AS target_type, m LIMIT 2000")
    return {"links": rows}


@app.get("/endpoints")
def endpoints() -> list[dict[str, object]]:
    return store.query("MATCH (e:Endpoint) RETURN e ORDER BY e.path")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "graph": settings.falkordb_graph}
