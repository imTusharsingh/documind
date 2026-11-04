from fastapi.testclient import TestClient

from app.main import create_app


def test_unknown_route_uses_the_error_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/unknown")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "NOT_FOUND",
            "message": "Not Found",
            "details": None,
        }
    }


def test_wrong_method_uses_the_error_envelope(client: TestClient) -> None:
    response = client.post("/api/v1/health")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_validation_error_uses_the_error_envelope() -> None:
    # A route is added to an isolated app so this test exercises the real
    # request pipeline (router -> FastAPI validation -> handler) rather
    # than calling the handler directly.
    app = create_app()

    @app.get("/api/v1/_validation-probe")
    def probe(count: int) -> dict[str, int]:
        return {"count": count}

    with TestClient(app) as test_client:
        response = test_client.get("/api/v1/_validation-probe", params={"count": "many"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "The request payload is invalid."
    assert isinstance(body["error"]["details"], list)
    assert body["error"]["details"][0]["loc"] == ["query", "count"]


def test_unhandled_exception_does_not_leak_internals() -> None:
    app = create_app()

    @app.get("/api/v1/_crash-probe")
    def crash() -> None:
        raise RuntimeError("secret internal detail")

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get("/api/v1/_crash-probe")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["message"] == "An unexpected error occurred."
    assert "secret internal detail" not in response.text
