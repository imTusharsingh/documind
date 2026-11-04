import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk, DocumentStatus
from app.repositories.search import SearchHit
from app.repositories.users import DEVELOPMENT_OWNER_ID
from app.services.evaluation import evaluate_case


def _hit(document_id: uuid.UUID, page_number: int) -> SearchHit:
    return SearchHit(
        chunk_id=uuid.uuid4(),
        document_id=document_id,
        document_name="paper.pdf",
        page_number=page_number,
        chunk_index=0,
        content="evidence",
        similarity=0.9,
    )


def test_evaluation_metrics_measure_recall_rank_and_page_match() -> None:
    document_id = uuid.uuid4()
    hits = [_hit(uuid.uuid4(), 1), _hit(document_id, 3), _hit(document_id, 2)]

    recall, reciprocal_rank, page_match = evaluate_case(
        hits,
        [(str(document_id), 2), (str(document_id), 3)],
    )

    assert recall == 1.0
    assert reciprocal_rank == 0.5
    assert page_match is True


def test_evaluation_metrics_return_zero_when_nothing_matches() -> None:
    hits = [_hit(uuid.uuid4(), 1)]

    assert evaluate_case(hits, [(str(uuid.uuid4()), 4)]) == (0.0, 0.0, False)


def test_persistent_dataset_saves_cases_and_historical_run(
    client: TestClient, session: Session, fake_embedder
) -> None:
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
            content="retrieval quality",
            token_count=2,
            embedding=fake_embedder._vector("retrieval quality"),
        )
    )
    session.flush()

    response = client.post(
        "/api/v1/evaluation/datasets",
        json={
            "name": "Quality checks",
            "cases": [
                {
                    "question": "What is retrieval quality?",
                    "expected_sources": [{"document_id": str(document_id), "page_number": 1}],
                }
            ],
        },
    )

    assert response.status_code == 201
    dataset_id = response.json()["id"]
    run = client.post(
        f"/api/v1/evaluation/datasets/{dataset_id}/runs",
        json={"top_k": 5, "label": "baseline", "embedding_model": "test-embedder"},
    )
    assert run.status_code == 201
    assert run.json()["recall_at_k"] == 1.0
    assert run.json()["label"] == "baseline"
    assert run.json()["embedding_model"] == "test-embedder"
    assert len(run.json()["results"]) == 1

    detail = client.get(f"/api/v1/evaluation/datasets/{dataset_id}")
    assert detail.status_code == 200
    assert detail.json()["run_count"] == 1

    trend = client.get(f"/api/v1/evaluation/datasets/{dataset_id}/trend")
    assert trend.status_code == 200
    assert trend.json()["runs"][0]["label"] == "baseline"
