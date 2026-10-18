from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from git import NULL_TREE, Repo

from .graph import store


def ingest_repo(repo_path: str, max_commits: int = 300) -> dict[str, int | str]:
    repo = Repo(repo_path)
    commits = list(repo.iter_commits(max_count=max_commits))
    graph_name = Path(repo.working_tree_dir or repo_path).name
    store.write("MERGE (r:Repo {name: $name})", {"name": graph_name})
    for commit in reversed(commits):
        author_email = commit.author.email or "unknown@example.com"
        author_name = commit.author.name or "Unknown"
        timestamp = datetime.fromtimestamp(commit.committed_date, timezone.utc).isoformat()
        store.write(
            """
            MERGE (a:Author {email: $email}) SET a.name=$name
            MERGE (c:Commit {sha: $sha}) SET c.message=$message, c.ts=$ts
            MERGE (a)-[:AUTHORED]->(c)
            """,
            {"email": author_email, "name": author_name, "sha": commit.hexsha,
             "message": commit.message.strip(), "ts": timestamp},
        )
        for parent in commit.parents[:1]:
            changes = commit.diff(parent, create_patch=False)
        if not commit.parents:
            changes = commit.diff(NULL_TREE, create_patch=False)
        for change in changes:
            path = change.b_path or change.a_path
            if not path:
                continue
            store.write(
                """
                MERGE (c:Commit {sha: $sha})
                MERGE (f:File {path: $path})
                MERGE (c)-[m:MODIFIED]->(f)
                SET m.additions=$additions, m.deletions=$deletions
                """,
                {"sha": commit.hexsha, "path": path, "additions": 0, "deletions": 0},
            )
    return {"repo": graph_name, "commits": len(commits)}
