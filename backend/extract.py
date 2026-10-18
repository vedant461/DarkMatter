from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Iterable

from .graph import store

log = logging.getLogger(__name__)


def _functions(tree: ast.AST) -> Iterable[ast.FunctionDef | ast.AsyncFunctionDef]:
    return (node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))


def extract_fastapi(repo_path: str) -> dict[str, int]:
    files: dict[str, ast.AST] = {}
    for path in Path(repo_path).rglob("*.py"):
        try:
            files[str(path.relative_to(repo_path)).replace("\\", "/")] = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError) as exc:
            log.warning("unresolved Python file %s: %s", path, exc)
    endpoints = 0
    for filename, tree in files.items():
        for node in _functions(tree):
            function_id = f"{filename}:{node.name}"
            store.write("MERGE (f:File {path:$file}) MERGE (fn:Function {id:$id}) SET fn.name=$name MERGE (f)-[:DEFINES]->(fn)",
                        {"file": filename, "id": function_id, "name": node.name})
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in {"get", "post", "put", "patch", "delete"} or not node.args:
                continue
            if not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[0].value, str):
                continue
            path = node.args[0].value
            endpoint_id = f"{node.func.attr.upper()} {path}"
            handler = next((item for item in _functions(tree) if item.lineno > node.lineno), None)
            handler_id = f"{filename}:{handler.name}" if handler else ""
            store.write(
                """
                MERGE (f:File {path:$file})
                MERGE (e:Endpoint {id:$id}) SET e.method=$method, e.path=$path, e.status='unknown'
                MERGE (f)-[:EXPOSES]->(e)
                """,
                {"file": filename, "id": endpoint_id, "method": node.func.attr.upper(), "path": path},
            )
            if handler_id:
                store.write("MERGE (fn:Function {id:$fn}) MERGE (e:Endpoint {id:$endpoint}) MERGE (e)-[:HANDLED_BY]->(fn)",
                            {"fn": handler_id, "endpoint": endpoint_id})
            endpoints += 1
    return {"files": len(files), "endpoints": endpoints}
