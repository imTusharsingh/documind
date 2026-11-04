"""PostgreSQL-backed ingestion worker.

Run with ``python -m app.workers.ingest``. It polls for pending
documents, claims one atomically, and processes it. There is no broker:
the documents table is the queue, and status transitions are the
protocol. That is durable across restarts without adding Redis or Celery
before they are justified.
"""

import logging
import time

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.models.document import Document
from app.repositories.documents import claim_next_document
from app.services.embeddings import create_embedding_provider
from app.services.ingestion import process_document
from app.services.workspace_settings import apply_workspace_settings, get_workspace_settings

logger = logging.getLogger("app.workers.ingest")


def run() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    logger.info("Ingestion worker started; polling every %.1fs", settings.worker_poll_seconds)
    while True:
        document_id = None
        try:
            with SessionLocal() as session:
                document_id = claim_next_document(session, settings.worker_stale_after_seconds)
                if document_id is not None:
                    logger.info("Claimed document %s", document_id)
                    document = session.get(Document, document_id)
                    if document is None:
                        continue
                    workspace = get_workspace_settings(session, document.owner_id, settings)
                    effective_settings = apply_workspace_settings(settings, workspace)
                    embedding_provider = create_embedding_provider(effective_settings)
                    process_document(session, document_id, effective_settings, embedding_provider)
                    logger.info("Finished document %s", document_id)
        except Exception:
            # A transient database failure or a bug in one document must not
            # kill the worker. The claim is durable, so a stuck document is
            # reclaimable after the stale threshold.
            logger.exception("Worker iteration failed; retrying")
            time.sleep(settings.worker_poll_seconds)
            continue

        if document_id is None:
            time.sleep(settings.worker_poll_seconds)


def main() -> None:
    try:
        run()
    except KeyboardInterrupt:
        logger.info("Ingestion worker stopped")


if __name__ == "__main__":
    main()
