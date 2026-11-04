"""Pure retrieval-evaluation metrics."""

from collections.abc import Iterable, Sequence

from app.repositories.search import SearchHit


def evaluate_case(
    hits: Sequence[SearchHit],
    expected_sources: Iterable[tuple[str, int]],
) -> tuple[float, float, bool]:
    """Return Recall@k, reciprocal rank, and exact page-match for one query."""
    expected = set(expected_sources)
    retrieved = [(str(hit.document_id), hit.page_number) for hit in hits]
    relevant = {source for source in retrieved if source in expected}
    recall = len(relevant) / len(expected) if expected else 0.0
    reciprocal_rank = next(
        (1 / rank for rank, source in enumerate(retrieved, start=1) if source in expected),
        0.0,
    )
    page_match = bool(relevant)
    return round(recall, 6), round(reciprocal_rank, 6), page_match
