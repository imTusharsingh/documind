import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk, DocumentStatus
from app.repositories.users import DEVELOPMENT_OWNER_ID


def _ready_document(session: Session, embedding: list[float]) -> uuid.UUID:
    document_id = uuid.uuid4()
    session.add(
        Document(
            id=document_id,
            owner_id=DEVELOPMENT_OWNER_ID,
            original_filename="research.pdf",
            content_type="application/pdf",
            size_bytes=100,
            storage_path=f"/tmp/{document_id}.pdf",
            status=DocumentStatus.READY,
            page_count=2,
            chunk_count=1,
        )
    )
    session.add(
        DocumentChunk(
            id=uuid.uuid4(),
            document_id=document_id,
            page_number=2,
            chunk_index=0,
            content="The research found a measurable improvement.",
            token_count=8,
            embedding=embedding,
        )
    )
    session.flush()
    return document_id


def test_chat_returns_validated_citations_and_persists_conversation(
    client: TestClient, session: Session, fake_embedder
) -> None:
    _ready_document(session, fake_embedder._vector("improvement"))

    response = client.post("/api/v1/chat", json={"question": "improvement"})

    assert response.status_code == 200
    body = response.json()
    assert body["insufficient_evidence"] is False
    assert body["citations"][0]["page_number"] == 2

    conversations = client.get("/api/v1/conversations")
    assert conversations.status_code == 200
    assert conversations.json()[0]["id"] == body["conversation_id"]

    detail = client.get(f"/api/v1/conversations/{body['conversation_id']}")
    assert detail.status_code == 200
    assert [message["role"] for message in detail.json()["messages"]] == ["user", "assistant"]
    assert detail.json()["messages"][1]["citations"][0]["page_number"] == 2


def test_chat_returns_insufficient_evidence_without_relevant_hits(
    client: TestClient,
) -> None:
    response = client.post("/api/v1/chat", json={"question": "Unknown topic"})

    assert response.status_code == 200
    body = response.json()
    assert body["insufficient_evidence"] is True
    assert body["citations"] == []
    assert "enough evidence" in body["answer"]
