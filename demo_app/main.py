import asyncio
from typing import Any

from fastapi import FastAPI, HTTPException

app = FastAPI(title="DarkMatter Demo Service")
chaos: dict[str, str] = {}


async def dependency(path: str) -> None:
    mode = chaos.get(path, "ok")
    if mode == "slow":
        await asyncio.sleep(6)
    if mode == "error":
        raise HTTPException(status_code=503, detail=f"simulated failure: {path}")


@app.get("/auth/verify")
async def verify() -> dict[str, str]:
    await dependency("/auth/verify")
    return {"status": "ok", "service": "auth"}


@app.get("/login")
async def login() -> dict[str, str]:
    await dependency("/auth/verify")
    return {"status": "ok", "service": "login"}


@app.get("/inventory")
async def inventory() -> dict[str, str]:
    await dependency("/auth/verify")
    return {"status": "ok", "service": "inventory"}


@app.get("/cart/{cart_id}")
async def cart(cart_id: str) -> dict[str, Any]:
    await dependency("/auth/verify")
    await dependency("/inventory")
    return {"status": "ok", "cart_id": cart_id}


@app.post("/payments/charge")
async def charge(payload: dict[str, Any] | None = None) -> dict[str, str]:
    await dependency("/auth/verify")
    return {"status": "ok", "service": "payments"}


@app.post("/checkout")
async def checkout(payload: dict[str, Any] | None = None) -> dict[str, str]:
    cart_id = str((payload or {}).get("cart_id", "42"))
    await dependency(f"/cart/{cart_id}")
    await dependency("/payments/charge")
    return {"status": "ok", "service": "checkout"}


@app.post("/_chaos")
async def set_chaos(payload: dict[str, str]) -> dict[str, str]:
    path, mode = payload.get("path", ""), payload.get("mode", "")
    if mode not in {"error", "slow", "ok"}:
        raise HTTPException(status_code=400, detail="mode must be error, slow, or ok")
    chaos[path] = mode
    return {"path": path, "mode": mode}
