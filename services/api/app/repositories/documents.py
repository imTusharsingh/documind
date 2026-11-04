"""Document queries and the ingestion claim protocol."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.document import Document, DocumentChunk, DocumentStatus


def create_document(
    session: Session,
    *,
    document_id: uuid.UUID,
    owner_id: uuid.UUID,
    original_filename: str,
    content_type: str,
    size_bytes: int,
    storage_path: str,
) -> Document:
    document = Document(
        id=document_id,
        owner_id=owner_id,
        original_filename=original_filename,
        content_type=content_type,
        size_bytes=size_bytes,
        storage_path=storage_path,
        status=DocumentStatus.PENDING,
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


def list_documents(
    session: Session,
    owner_id: uuid.UUID,
    status: DocumentStatus | None = None,
) -> list[Document]:
    statement = select(Document).where(Document.owner_id == owner_id)
    if status is not None:
        statement = statement.where(Document.status == status)
    statement = statement.order_by(Document.created_at.desc(), Document.id)
    return list(session.scalars(statement))


def get_document(session: Session, owner_id: uuid.UUID, document_id: uuid.UUID) -> Document:
    document = session.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.owner_id == owner_id,
        )
    )
    if document is None:
        raise NotFoundError("Document was not found.")
    return document


def delete_document(session: Session, owner_id: uuid.UUID, document_id: uuid.UUID) -> Document:
    document = get_document(session, owner_id, document_id)
    session.delete(document)
    session.commit()
    return document


def claim_next_document(session: Session, stale_after_seconds: int) -> uuid.UUID | None:
    """Atomically move one pending document into processing.

    ``FOR UPDATE SKIP LOCKED`` lets several workers poll concurrently
    without blocking each other and without handing the same row to two
    workers. Documents stuck in processing past the stale threshold are
    reclaimable, so a crashed worker does not strand them forever.

    The claim commits before returning: holding the row lock for the
    duration of PDF extraction and embedding would serialize all workers.
    """
    stale_before = datetime.now(UTC) - timedelta(seconds=stale_after_seconds)

    candidate = (
        select(Document.id)
        .where(
            or_(
                Document.status == DocumentStatus.PENDING,
                and_(
                    Document.status == DocumentStatus.PROCESSING,
                    Document.processing_started_at < stale_before,
                ),
            )
        )
        .order_by(Document.created_at, Document.id)
        .limit(1)
        .with_for_update(skip_locked=True)
        .scalar_subquery()
    )

    statement = (
        update(Document)
        .where(Document.id == candidate)
        .values(
            status=DocumentStatus.PROCESSING,
            processing_started_at=func.now(),
            updated_at=func.now(),
            page_count=None,
            chunk_count=None,
            error_message=None,
        )
        .returning(Document.id)
    )

    document_id = session.execute(statement).scalar_one_or_none()
    session.commit()
    return document_id


def replace_chunks(
    session: Session,
    document_id: uuid.UUID,
    chunks: list[tuple[int, int, str, int]],
) -> None:
    """Replace all chunks for a document.

    Deleting first makes retries idempotent: a worker that crashed after
    writing some chunks leaves no duplicates when it is reclaimed.
    """
    session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
    session.add_all(
        [
            DocumentChunk(
                id=uuid.uuid4(),
                document_id=document_id,
                page_number=page_number,
                chunk_index=chunk_index,
                content=content,
                token_count=token_count,
            )
            for page_number, chunk_index, content, token_count in chunks
        ]
    )


def mark_ready(
    session: Session,
    document_id: uuid.UUID,
    *,
    page_count: int,
    chunk_count: int,
) -> None:
    document = session.get(Document, document_id)
    if document is None:
        return

    document.status = DocumentStatus.READY
    document.page_count = page_count
    document.chunk_count = chunk_count
    document.error_message = None
    document.processed_at = datetime.now(UTC)
    session.commit()


def mark_failed(session: Session, document_id: uuid.UUID, message: str) -> None:
    document = session.get(Document, document_id)
    if document is None:
        return

    document.status = DocumentStatus.FAILED
    document.error_message = message[:1000]
    document.processed_at = datetime.now(UTC)
    session.commit()
