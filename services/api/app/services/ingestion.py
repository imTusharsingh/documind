"""Document ingestion orchestration.

Called by the worker after a document has been claimed. Extraction,
chunking, and embedding happen outside the claim transaction; the final
state change is committed only when the document is fully processed.
"""

import logging
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.document import Document
from app.repositories.documents import mark_failed, mark_ready, replace_chunks
from app.services.chunking import ChunkingConfig, chunk_pages
from app.services.embeddings import (
    EmbeddingConfigurationError,
    EmbeddingProvider,
    EmbeddingProviderError,
)
from app.services.extraction import ExtractionError, extract_pages

logger = logging.getLogger(__name__)


def process_document(
    session: Session,
    document_id: uuid.UUID,
    settings: Settings,
    embedding_provider: EmbeddingProvider,
) -> None:
    """Extract, chunk, embed, and persist a claimed document.

    Every failure is recorded on the document row so the UI can explain
    what happened. Worker logs keep the traceback; the document keeps a
    user-facing message.
    """
    document = session.get(Document, document_id)
    if document is None:
        logger.warning("Document %s disappeared before processing", document_id)
        return

    try:
        pages = extract_pages(Path(document.storage_path))
        drafts = chunk_pages(
            pages,
            ChunkingConfig(
                chunk_tokens=settings.chunk_tokens,
                overlap_tokens=settings.chunk_overlap_tokens,
            ),
        )
        embeddings = embedding_provider.embed_texts([draft.content for draft in drafts])

        if len(embeddings) != len(drafts):
            raise EmbeddingProviderError(
                "The embedding provider returned the wrong number of vectors."
            )

        replace_chunks(
            session,
            document_id,
            [
                (
                    draft.page_number,
                    draft.chunk_index,
                    draft.content,
                    draft.token_count,
                    embedding,
                )
                for draft, embedding in zip(drafts, embeddings, strict=True)
            ],
        )
        mark_ready(
            session,
            document_id,
            page_count=len(pages),
            chunk_count=len(drafts),
        )
    except EmbeddingConfigurationError as exc:
        session.rollback()
        logger.warning("Embeddings are not configured for %s: %s", document_id, exc)
        mark_failed(session, document_id, str(exc))
    except EmbeddingProviderError as exc:
        session.rollback()
        logger.warning("Embedding request failed for %s: %s", document_id, exc)
        mark_failed(session, document_id, str(exc))
    except ExtractionError as exc:
        session.rollback()
        logger.warning("Extraction failed for %s: %s", document_id, exc)
        mark_failed(session, document_id, str(exc))
    except Exception:
        session.rollback()
        logger.exception("Unexpected ingestion failure for %s", document_id)
        mark_failed(session, document_id, "Ingestion failed unexpectedly. Check worker logs.")
