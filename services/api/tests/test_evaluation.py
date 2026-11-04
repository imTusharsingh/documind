import uuid

from app.repositories.search import SearchHit
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
