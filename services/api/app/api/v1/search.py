import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_owner, get_embedding_provider
from app.core.db import get_session
from app.core.errors import EmbeddingUnavailableError
from app.models.user import User
from app.repositories.search import search_chunks
from app.schemas.errors import ErrorResponse
from app.schemas.search import SearchRequest, SearchResponse, SearchResult
from app.services.embeddings import (
    EmbeddingConfigurationError,
    EmbeddingProvider,
    EmbeddingProviderError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=SearchResponse,
    summary="Search document chunks",
    description=(
        "Embeds the query and returns the closest passages from ready documents "
        "using cosine similarity in pgvector."
    ),
    responses={
        503: {
            "model": ErrorResponse,
            "description": "The embedding provider is not configured or unavailable.",
        }
    },
)
def search_documents(
    request: SearchRequest,
    session: Annotated[Session, Depends(get_session)],
    owner: Annotated[User, Depends(get_current_owner)],
    embedding_provider: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
) -> SearchResponse:
    try:
        vectors = embedding_provider.embed_texts([request.query])
    except EmbeddingConfigurationError as exc:
        raise EmbeddingUnavailableError(str(exc)) from exc
    except EmbeddingProviderError as exc:
        logger.warning("Search embedding failed: %s", exc)
        raise EmbeddingUnavailableError(str(exc)) from exc

    if len(vectors) != 1:
        raise EmbeddingUnavailableError("The embedding provider returned no query vector.")

    hits = search_chunks(
        session,
        owner_id=owner.id,
        query_embedding=vectors[0],
        limit=request.limit,
        document_ids=request.document_ids,
        min_similarity=request.min_similarity,
    )

    return SearchResponse(
        query=request.query,
        results=[
            SearchResult(
                document_id=hit.document_id,
                document_name=hit.document_name,
                page_number=hit.page_number,
                chunk_index=hit.chunk_index,
                content=hit.content,
                similarity=hit.similarity,
            )
            for hit in hits
        ],
    )
