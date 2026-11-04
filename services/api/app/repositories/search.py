"""Semantic search over ready document chunks."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk, DocumentStatus


@dataclass(frozen=True)
class SearchHit:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    page_number: int
    chunk_index: int
    content: str
    similarity: float


def search_chunks(
    session: Session,
    *,
    owner_id: uuid.UUID,
    query_embedding: Sequence[float],
    limit: int,
    document_ids: Sequence[uuid.UUID] = (),
    min_similarity: float = 0.0,
) -> list[SearchHit]:
    """Return the closest ready chunks using cosine distance in pgvector.

    The distance operator runs in PostgreSQL, not in Python, so the HNSW
    index can be used and owner/ready filters stay inside one SQL statement.
    """
    distance = DocumentChunk.embedding.cosine_distance(list(query_embedding))

    statement = (
        select(
            DocumentChunk.id,
            Document.id,
            Document.original_filename,
            DocumentChunk.page_number,
            DocumentChunk.chunk_index,
            DocumentChunk.content,
            distance.label("distance"),
        )
        .select_from(DocumentChunk)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(
            Document.owner_id == owner_id,
            Document.status == DocumentStatus.READY,
            DocumentChunk.embedding.is_not(None),
        )
    )

    if document_ids:
        statement = statement.where(Document.id.in_(list(document_ids)))

    if min_similarity > 0:
        statement = statement.where(distance <= 1 - min_similarity)

    statement = statement.order_by(distance, DocumentChunk.id).limit(limit)

    return [
        SearchHit(
            chunk_id=chunk_id,
            document_id=document_id,
            document_name=document_name,
            page_number=page_number,
            chunk_index=chunk_index,
            content=content,
            similarity=round(min(1.0, max(0.0, 1 - float(chunk_distance))), 6),
        )
        for (
            chunk_id,
            document_id,
            document_name,
            page_number,
            chunk_index,
            content,
            chunk_distance,
        ) in session.execute(statement).all()
    ]
