"""Add chunk embeddings and the pgvector similarity index.

Ready documents from Milestone 2 predate embeddings, so they are requeued.
The worker replaces their chunks and embeds them again before marking them
ready; leaving them ready would make them silently invisible to search.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIMENSIONS = 1536


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column(
        "document_chunks",
        sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=True),
    )
    op.create_index(
        "ix_document_chunks_embedding_hnsw",
        "document_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    # Existing chunks have no vectors. Requeue every ready document so the
    # worker regenerates its chunks with embeddings.
    op.execute(
        """
        UPDATE documents
        SET status = 'pending',
            processing_started_at = NULL,
            processed_at = NULL,
            page_count = NULL,
            chunk_count = NULL,
            error_message = NULL,
            updated_at = now()
        WHERE status = 'ready'
        """
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_embedding_hnsw", table_name="document_chunks")
    op.drop_column("document_chunks", "embedding")
