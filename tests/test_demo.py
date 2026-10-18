from fastapi.testclient import TestClient

from demo_app.main import app


def test_chain_is_healthy() -> None:
    client = TestClient(app)
    assert client.get("/login").status_code == 200
    assert client.get("/cart/42").status_code == 200


def test_failure_propagates() -> None:
    client = TestClient(app)
    client.post("/_chaos", json={"path": "/auth/verify", "mode": "error"})
    assert client.get("/login").status_code == 503
    assert client.get("/cart/42").status_code == 503
    client.post("/_chaos", json={"path": "/auth/verify", "mode": "ok"})
