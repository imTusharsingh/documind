from fastapi.testclient import TestClient

from app.api.v1 import health as health_module
from app.schemas.health import DependencyStatus


def test_liveness_does_not_check_dependencies(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "DocuMind API"
    assert body["dependencies"] == {}


def test_readiness_reports_database_up(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["dependencies"]["database"]["status"] == "up"
    assert body["dependencies"]["database"]["latency_ms"] is not None
    assert body["dependencies"]["database"]["error"] is None


def test_readiness_is_degraded_when_database_is_down(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        health_module,
        "check_database",
        lambda _: DependencyStatus(status="down", error="Database connection failed."),
    )

    response = client.get("/api/v1/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["dependencies"]["database"]["status"] == "down"
    assert body["dependencies"]["database"]["error"] == "Database connection failed."


def test_openapi_schema_lists_current_routes(client: TestClient) -> None:
    response = client.get("/api/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/health" in paths
    assert "/api/v1/health/live" in paths
    assert "/api/v1/me" in paths
