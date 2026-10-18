from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import settings
from .extract import extract_fastapi
from .graph import store
from .ingest import ingest_repo
from .monitor import probe_once
from .triage import deterministic_triage, send_alert

app = FastAPI(title="DarkMatter")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class IngestRequest(BaseModel):
    repo: str
    max_commits: int = 300


class SimulationRequest(BaseModel):
    path: str


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


@app.get("/incidents")
def incidents() -> list[dict[str, object]]:
    return store.query("MATCH (i:Incident) RETURN i ORDER BY i.opened_at DESC")


@app.get("/incidents/{incident_id}")
def incident(incident_id: str) -> dict[str, object]:
    found = store.query("MATCH (i:Incident {id:$id}) RETURN i", {"id": incident_id})
    if not found:
        raise HTTPException(404, "incident not found")
    return {"incident": found[0], "triage": deterministic_triage(incident_id)}


@app.post("/incidents/{incident_id}/send-email")
def incident_email(incident_id: str, payload: dict[str, object]) -> dict[str, object]:
    return send_alert(incident_id, [str(x) for x in payload.get("recipients", [])],
                      str(payload.get("subject", "DarkMatter incident")), str(payload.get("body", "")))


@app.post("/simulate-failure")
async def simulate_failure(request: SimulationRequest) -> dict[str, object]:
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.post(settings.demo_base_url + "/_chaos", json={"path": request.path, "mode": "error"})
    return {"simulated": "failure", "path": request.path, "status": response.status_code}


@app.post("/simulate-recover")
async def simulate_recover(request: SimulationRequest) -> dict[str, object]:
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.post(settings.demo_base_url + "/_chaos", json={"path": request.path, "mode": "ok"})
    return {"simulated": "recover", "path": request.path, "status": response.status_code}


@app.post("/monitor")
async def monitor() -> list[dict[str, object]]:
    return await probe_once()
