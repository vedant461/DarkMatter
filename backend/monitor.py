from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
import yaml

from .config import settings
from .graph import store
from .triage import open_incident

failures: dict[str, int] = {}


async def probe_once(config_path: str = "probes.yaml") -> list[dict[str, Any]]:
    config = yaml.safe_load(open(config_path, encoding="utf-8"))
    results = []
    async with httpx.AsyncClient(timeout=5) as client:
        for probe in config.get("endpoints", []):
            started = time.perf_counter()
            try:
                response = await client.request(probe["method"], config["base_url"] + probe["path"], json=probe.get("body"))
                latency = round((time.perf_counter() - started) * 1000)
                expected = probe.get("expect", {}).get("status", 200)
                ok = response.status_code == expected and latency <= probe.get("expect", {}).get("max_latency_ms", 5000)
            except httpx.HTTPError:
                response, latency, ok = None, 5000, False
            endpoint_id = f"{probe['method']} {probe['path']}"
            failures[endpoint_id] = 0 if ok else failures.get(endpoint_id, 0) + 1
            status = "failing" if failures[endpoint_id] >= 3 else "ok"
            store.write("MERGE (e:Endpoint {id:$id}) SET e.status=$status, e.last_checked=$checked, e.latency_ms=$latency, e.fail_count=$count",
                        {"id": endpoint_id, "status": status, "checked": time.time(), "latency": latency, "count": failures[endpoint_id]})
            results.append({"id": endpoint_id, "ok": ok, "status": status, "latency_ms": latency})
    if any(item["status"] == "failing" for item in results):
        existing = store.query("MATCH (i:Incident {status:'open'}) RETURN i.id AS id LIMIT 1")
        if not existing:
            open_incident()
    return results
