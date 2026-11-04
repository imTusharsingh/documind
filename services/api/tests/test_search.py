import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk, DocumentStatus
from app.repositories.users import DEVELOPMENT_OWNER_ID


def _ready_document(session: Session, name: str, content: str, embedding: list[float]) -> uuid.UUID:
    document_id = uuid.uuid4()
    session.add(
        Document(
            id=document_id,
            owner_id=DEVELOPMENT_OWNER_ID,
            original_filename=name,
            content_type="application/pdf",
            size_bytes=100,
            storage_path=f"/tmp/{document_id}.pdf",
            status=DocumentStatus.READY,
            page_count=1,
            chunk_count=1,
        )
    )
    session.add(
        DocumentChunk(
            id=uuid.uuid4(),
            document_id=document_id,
            page_number=1,
            chunk_index=0,
            content=content,
            token_count=3,
            embedding=embedding,
        )
    )
    session.flush()
    return document_id


def test_search_returns_ready_chunks_ranked_by_similarity(
    client: TestClient, session: Session, fake_embedder
) -> None:
    matching_id = _ready_document(
        session, "matching.pdf", "matching passage", fake_embedder._vector("matching")
    )
    _ready_document(session, "other.pdf", "other passage", fake_embedder._vector("other"))

    response = client.post("/api/v1/search", json={"query": "matching", "limit": 5})

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "matching"
    assert body["results"][0]["document_id"] == str(matching_id)
    assert body["results"][0]["similarity"] == 1.0


def test_search_filters_by_document_and_similarity(
    client: TestClient, session: Session, fake_embedder
) -> None:
    matching_id = _ready_document(
        session, "matching.pdf", "matching passage", fake_embedder._vector("matching")
    )
    _ready_document(session, "other.pdf", "other passage", fake_embedder._vector("other"))

    response = client.post(
        "/api/v1/search",
        json={
            "query": "matching",
            "document_ids": [str(matching_id)],
            "min_similarity": 0.9,
        },
    )

    assert response.status_code == 200
    assert [result["document_id"] for result in response.json()["results"]] == [str(matching_id)]


def test_search_rejects_blank_queries(client: TestClient) -> None:
    response = client.post("/api/v1/search", json={"query": "   "})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
