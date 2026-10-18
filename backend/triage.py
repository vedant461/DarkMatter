from __future__ import annotations

import math
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any, TypedDict
from uuid import uuid4

from .config import settings
from .graph import store


class Triage(TypedDict):
    root_causes: list[dict[str, Any]]
    impacted: list[dict[str, Any]]
    owners: list[dict[str, Any]]
    explanation: str
    email_subject: str
    email_body: str


def find_root_cause() -> list[dict[str, Any]]:
    return store.query(
        """
        MATCH (root:Endpoint {status:'failing'})
        WHERE NOT (root)-[:DEPENDS_ON]->(:Endpoint {status:'failing'})
        RETURN root.id AS id, root.path AS path, root.tier AS tier
        """
    )


def get_blast_radius(root: str) -> list[dict[str, Any]]:
    return store.query(
        """
        MATCH p=(dependent:Endpoint)-[:DEPENDS_ON*1..]->(root:Endpoint {id:$root})
        RETURN dependent.id AS id, dependent.path AS path,
               dependent.status AS status, nodes(p) AS path_nodes
        ORDER BY length(p)
        """,
        {"root": root},
    )


def rank_criticality() -> list[dict[str, Any]]:
    rows = store.query("MATCH (e:Endpoint) OPTIONAL MATCH (e)-[:DEPENDS_ON]->(d:Endpoint) RETURN e.id AS id, count(d) AS dependents, e.category AS category")
    maximum = max(max((int(row["dependents"]) for row in rows), default=0), 1)
    for row in rows:
        category = str(row.get("category") or "read-only").lower()
        boost = 1.5 if category in {"auth", "payment", "checkout"} else 1.0 if category == "read-only" else 0.5
        importance = round((int(row["dependents"]) / maximum) * boost, 3)
        tier = "P0" if importance >= 1.3 else "P1" if importance >= 0.8 else "P2" if importance >= 0.3 else "P3"
        store.write("MATCH (e:Endpoint {id:$id}) SET e.importance=$importance, e.tier=$tier", {"id": row["id"], "importance": importance, "tier": tier})
        row.update(importance=importance, tier=tier)
    return rows


def get_owners(endpoint: str, half_life_days: int = 90, k: int = 5) -> list[dict[str, Any]]:
    rows = store.query(
        """
        MATCH (e:Endpoint {id:$endpoint})-[:HANDLED_BY]->(fn:Function)
        MATCH (f:File)-[:DEFINES|EXPOSES]->(fn)
        MATCH (a:Author)-[:AUTHORED]->(c:Commit)-[m:MODIFIED]->(f)
        WHERE NOT toLower(a.email) CONTAINS 'bot' AND NOT toLower(a.email) CONTAINS 'noreply'
        RETURN a.email AS email, a.name AS name, f.path AS file, c.sha AS commit, c.ts AS ts,
               sum(exp(-log(2) * duration.inDays(date(c.ts), date()).days / $half_life) *
                   (1 + log(1 + coalesce(m.additions,0) + coalesce(m.deletions,0)))) AS score
        ORDER BY score DESC LIMIT $k
        """,
        {"endpoint": endpoint, "half_life": half_life_days, "k": k},
    )
    return rows


def send_alert(incident_id: str, recipients: list[str], subject: str, body: str) -> dict[str, Any]:
    valid = [email for email in recipients if email.lower() in settings.allowlist]
    if not valid:
        raise ValueError("no recipients are present in ALERT_ALLOWLIST")
    if not settings.dry_run and settings.smtp_host:
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = settings.from_email, ", ".join(valid), subject
        message.set_content(body)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
    store.write(
        "MATCH (i:Incident {id:$id}) UNWIND $emails AS email MERGE (a:Author {email:email}) MERGE (i)-[:NOTIFIED {score:1}]->(a)",
        {"id": incident_id, "emails": valid},
    )
    return {"dry_run": settings.dry_run, "recipients": valid}


def deterministic_triage(incident_id: str) -> Triage:
    roots = find_root_cause()
    impacted: list[dict[str, Any]] = []
    for root in roots:
        impacted.extend(get_blast_radius(str(root["id"])))
    rank_criticality()
    for item in impacted:
        endpoint = item["id"]
        tier = store.query("MATCH (e:Endpoint {id:$id}) RETURN e.tier AS tier", {"id": endpoint})
        item["tier"] = tier[0].get("tier", "P3") if tier else "P3"
        item["failing"] = item.get("status") == "failing"
    owners = []
    for root in roots:
        owners.extend(get_owners(str(root["id"])))
    paths = [f"{root['id']} -> " + " -> ".join(str(i["id"]) for i in impacted if i["id"] != root["id"]) for root in roots]
    explanation = "Graph path evidence: " + ("; ".join(paths) if paths else "no dependency path found")
    body = "\n".join(["DarkMatter incident alert", "", explanation, "", "Impacted endpoints by tier:"] + [f"- {x['tier']}: {x['id']}" for x in sorted(impacted, key=lambda x: x["tier"])])
    result: Triage = {"root_causes": roots, "impacted": impacted, "owners": owners, "explanation": explanation,
                      "email_subject": f"[DarkMatter] Incident {incident_id}", "email_body": body}
    store.write("MATCH (i:Incident {id:$id}) SET i.explanation=$explanation RETURN i", {"id": incident_id, "explanation": explanation})
    for root in roots:
        store.write("MATCH (i:Incident {id:$incident}), (e:Endpoint {id:$endpoint}) MERGE (i)-[:ROOT_CAUSE]->(e)", {"incident": incident_id, "endpoint": root["id"]})
    return result


def open_incident() -> tuple[str, Triage]:
    incident_id = str(uuid4())
    store.write("CREATE (i:Incident {id:$id, opened_at:$opened, status:'open'})", {"id": incident_id, "opened": datetime.now(timezone.utc).isoformat()})
    return incident_id, deterministic_triage(incident_id)
