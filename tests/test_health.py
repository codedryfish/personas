from fastapi.testclient import TestClient

from persona_sim.app.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "environment" in body
    assert body["database"] in {"ok", "unavailable"}
