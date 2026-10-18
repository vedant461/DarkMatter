# DarkMatter

DarkMatter is a FalkorDB-backed on-call demo for FalkorDB Graph Hacks Track 01. It ingests repository history and FastAPI structure, probes a live service, then explains incidents with graph paths, impact tiers, and owner evidence.

## Run

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open http://localhost:5173. The backend is http://localhost:8000 and the demo service is http://localhost:8001. To create the seeded repository, run `python seed_history.py`, then POST `{"repo":"demo_history"}` to `/ingest`.

The default email mode is `DRY_RUN=true`; recipients must also be in `ALERT_ALLOWLIST`. The UI labels simulated failures and dry-run alerts explicitly.

## Architecture and graph decisions

The FastAPI backend writes one FalkorDB graph per configured repo. `Author`, `Commit`, `File`, `Function`, `Endpoint`, and `Incident` nodes are connected with the schema in the challenge brief. Ingestion uses MERGE and parameterized values, so rerunning it is idempotent. FastAPI extraction is deliberately AST-only.

Operational decisions are Cypher decisions: roots are failing endpoints with no failing `DEPENDS_ON` target; blast radius is the reverse shortest dependency path; importance is PageRank-compatible dependent centrality with a deterministic dependent-count fallback; owners are scored from recent weighted `MODIFIED` evidence and bots/noreply authors are excluded. The LLM adapter is intentionally optional; deterministic templates keep the same JSON output shape when no key/provider is configured.

## Demo script

1. Start compose and ingest `demo_history`.
2. Select `/auth/verify`, click **SIMULATE FAILURE**, and repeat the monitor request three times (`POST /monitor`) to cross the failure threshold.
3. Open the incident to see root path evidence, impact tiers, owner evidence, and the editable dry-run email.
4. Click **SIMULATE RECOVER** and probe again.

## Example Cypher

```cypher
MATCH (a:Author)-[:AUTHORED]->(c:Commit) RETURN a.email, count(c)
MATCH (c:Commit)-[:MODIFIED]->(f:File) RETURN c.sha, f.path
MATCH p=(d:Endpoint)-[:DEPENDS_ON*1..]->(r:Endpoint) RETURN p
MATCH (e:Endpoint) RETURN e.id, e.tier, e.importance ORDER BY e.importance DESC
MATCH (i:Incident)-[:ROOT_CAUSE]->(e:Endpoint) RETURN i.id, e.id
```

## Limitations and next steps

Extraction currently targets FastAPI and standard-library AST patterns; live detection needs a runnable service plus `probes.yaml`. Ingestion works on any git repository, but non-Python repositories only receive git history. Next steps are CI-test webhooks, log ingestion, more frameworks, and PR/issue nodes. This is not production hardening and has no auth, webhooks, Slack, OpenTelemetry, auto-fix, or multi-repo UI.
