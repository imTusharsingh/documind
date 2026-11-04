import uuid

from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.users import DEVELOPMENT_OWNER_ID


def test_returns_the_seeded_development_owner(client: TestClient) -> None:
    response = client.get("/api/v1/me")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(DEVELOPMENT_OWNER_ID)
    assert body["email"] == "owner@documind.local"
    assert body["display_name"] == "Development Owner"
    assert body["created_at"]


def test_reports_a_missing_owner_explicitly(client: TestClient, session: Session) -> None:
    session.execute(delete(User).where(User.id == uuid.UUID(str(DEVELOPMENT_OWNER_ID))))
    session.flush()
    session.expunge_all()

    response = client.get("/api/v1/me")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "DEVELOPMENT_OWNER_MISSING"
    assert "alembic upgrade head" in body["error"]["message"]
