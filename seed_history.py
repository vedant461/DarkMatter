from datetime import datetime, timedelta, timezone
from pathlib import Path
from git import Actor, Repo

repo = Repo.init(Path("demo_history"))
authors = [Actor("Ada Owner", "ada@example.com"), Actor("Grace Builder", "grace@example.com"), Actor("Lin Reviewer", "lin@example.com"), Actor("Build Bot", "build-bot@noreply.example.com")]
base = datetime.now(timezone.utc) - timedelta(days=90)
for index in range(40):
    path = Path("demo_history") / ("service.py" if index % 3 == 0 else "routes.py" if index % 3 == 1 else "README.md")
    path.write_text(f"change {index}\n", encoding="utf-8")
    repo.index.add([path.name])
    actor = authors[index % len(authors)]
    when = base + timedelta(days=index * 2)
    repo.index.commit(f"demo change {index}", author=actor, committer=actor,
                      author_date=when.strftime("%Y-%m-%d %H:%M:%S %z"),
                      commit_date=when.strftime("%Y-%m-%d %H:%M:%S %z"))
print("seeded 40 commits in demo_history")
