import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.repositories.documents import claim_next_document, create_document
from app.repositories.users import DEVELOPMENT_OWNER_ID
from app.services.ingestion import process_document


def _create_pending_document(
    session: Session,
    pdf_path: Path,
    *,
    name: str = "document.pdf",
) -> uuid.UUID:
    document = create_document(
        session,
        document_id=uuid.uuid4(),
        owner_id=DEVELOPMENT_OWNER_ID,
        original_filename=name,
        content_type="application/pdf",
        size_bytes=pdf_path.stat().st_size if pdf_path.exists() else 0,
        storage_path=str(pdf_path),
    )
    return document.id


def test_process_document_extracts_chunks_and_marks_ready(
    session: Session,
    pdf_factory,
    tmp_path: Path,
    test_settings: Settings,
) -> None:
    path = pdf_factory(
        tmp_path / "ingest.pdf",
        ["First page text with enough words to chunk.", "Second page text."],
    )
    document_id = _create_pending_document(session, path)

    process_document(session, document_id, test_settings)

    session.expire_all()
    document = session.get(Document, document_id)
    assert document is not None
    assert document.status == DocumentStatus.READY
    assert document.page_count == 2
    assert document.chunk_count and document.chunk_count >= 2
    assert document.error_message is None

    chunks = list(
        session.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
    )
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert {chunk.page_number for chunk in chunks} == {1, 2}
    assert all(chunk.token_count > 0 and chunk.content for chunk in chunks)


def test_scanned_pdf_fails_with_an_explicit_message(
    session: Session,
    pdf_factory,
    tmp_path: Path,
    test_settings: Settings,
) -> None:
    path = pdf_factory(tmp_path / "scanned.pdf", ["", ""])
    document_id = _create_pending_document(session, path)

    process_document(session, document_id, test_settings)

    session.expire_all()
    document = session.get(Document, document_id)
    assert document is not None
    assert document.status == DocumentStatus.FAILED
    assert document.error_message is not None
    assert "Scanned PDFs are not supported" in document.error_message
    assert document.page_count is None


def test_claim_hands_each_document_to_one_worker(
    session: Session,
    pdf_factory,
    tmp_path: Path,
) -> None:
    first = _create_pending_document(session, tmp_path / "one.pdf", name="one.pdf")
    second = _create_pending_document(session, tmp_path / "two.pdf", name="two.pdf")

    claimed_first = claim_next_document(session, stale_after_seconds=300)
    claimed_second = claim_next_document(session, stale_after_seconds=300)
    claimed_none = claim_next_document(session, stale_after_seconds=300)

    assert {claimed_first, claimed_second} == {first, second}
    assert claimed_none is None

    session.expire_all()
    statuses = {document.id: document.status for document in session.scalars(select(Document))}
    assert statuses[first] == DocumentStatus.PROCESSING
    assert statuses[second] == DocumentStatus.PROCESSING


def test_stale_processing_documents_are_reclaimable(
    session: Session,
    pdf_factory,
    tmp_path: Path,
) -> None:
    path = pdf_factory(tmp_path / "stale.pdf", ["Stale document."])
    document_id = _create_pending_document(session, path)

    document = session.get(Document, document_id)
    assert document is not None
    document.status = DocumentStatus.PROCESSING
    document.processing_started_at = datetime.now(UTC) - timedelta(seconds=999)
    session.flush()

    claimed = claim_next_document(session, stale_after_seconds=300)

    assert claimed == document_id


def test_fresh_processing_documents_are_not_reclaimed(
    session: Session,
    pdf_factory,
    tmp_path: Path,
) -> None:
    path = pdf_factory(tmp_path / "busy.pdf", ["Busy document."])
    document_id = _create_pending_document(session, path)

    document = session.get(Document, document_id)
    assert document is not None
    document.status = DocumentStatus.PROCESSING
    document.processing_started_at = datetime.now(UTC)
    session.flush()

    assert claim_next_document(session, stale_after_seconds=300) is None


def test_chunk_count_matches_stored_rows(
    session: Session,
    pdf_factory,
    tmp_path: Path,
    test_settings: Settings,
) -> None:
    path = pdf_factory(tmp_path / "counts.pdf", ["Counted content on a single page."])
    document_id = _create_pending_document(session, path)

    process_document(session, document_id, test_settings)

    session.expire_all()
    document = session.get(Document, document_id)
    stored = session.scalar(
        select(func.count())
        .select_from(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
    )
    assert document is not None
    assert document.chunk_count == stored
