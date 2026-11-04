import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_owner, get_embedding_provider
from app.core.db import get_session
from app.core.errors import EmbeddingUnavailableError
from app.models.user import User
from app.repositories.search import search_chunks
from app.schemas.evaluation import (
    EvaluationCaseResult,
    EvaluationRequest,
    EvaluationResponse,
    RetrievedSource,
)
from app.services.embeddings import (
    EmbeddingConfigurationError,
    EmbeddingProvider,
    EmbeddingProviderError,
)
from app.services.evaluation import evaluate_case

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/evaluation/run", response_model=EvaluationResponse)
def run_evaluation(
    request: EvaluationRequest,
    session: Annotated[Session, Depends(get_session)],
    owner: Annotated[User, Depends(get_current_owner)],
    embedding_provider: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
) -> EvaluationResponse:
    try:
        vectors = embedding_provider.embed_texts([case.question for case in request.cases])
    except (EmbeddingConfigurationError, EmbeddingProviderError) as exc:
        logger.warning("Evaluation embedding failed: %s", exc)
        raise EmbeddingUnavailableError(str(exc)) from exc

    if len(vectors) != len(request.cases):
        raise EmbeddingUnavailableError(
            "The embedding provider returned the wrong number of vectors."
        )

    results: list[EvaluationCaseResult] = []
    for case, vector in zip(request.cases, vectors, strict=True):
        expected = {
            (str(source.document_id), source.page_number) for source in case.expected_sources
        }
        hits = search_chunks(
            session,
            owner_id=owner.id,
            query_embedding=vector,
            limit=request.top_k,
            min_similarity=request.min_similarity,
        )
        recall, reciprocal_rank, page_match = evaluate_case(hits, expected)
        results.append(
            EvaluationCaseResult(
                question=case.question,
                recall_at_k=recall,
                reciprocal_rank=reciprocal_rank,
                page_match=page_match,
                retrieved_sources=[
                    RetrievedSource(
                        chunk_id=hit.chunk_id,
                        document_id=hit.document_id,
                        document_name=hit.document_name,
                        page_number=hit.page_number,
                        chunk_index=hit.chunk_index,
                        similarity=hit.similarity,
                    )
                    for hit in hits
                ],
            )
        )

    count = len(results)
    return EvaluationResponse(
        case_count=count,
        recall_at_k=round(sum(result.recall_at_k for result in results) / count, 6),
        mean_reciprocal_rank=round(sum(result.reciprocal_rank for result in results) / count, 6),
        page_match_rate=round(sum(result.page_match for result in results) / count, 6),
        results=results,
    )
