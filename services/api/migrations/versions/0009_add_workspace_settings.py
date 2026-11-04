"""Add owner-scoped workspace settings."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_add_workspace_settings"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspace_settings",
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("openai_api_key", sa.Text(), nullable=True),
        sa.Column("llm_model", sa.Text(), nullable=False),
        sa.Column("embedding_model", sa.Text(), nullable=False),
        sa.Column("embedding_dim", sa.Integer(), nullable=False),
        sa.Column("embedding_batch_size", sa.Integer(), nullable=False),
        sa.Column("embedding_timeout_seconds", sa.Float(), nullable=False),
        sa.Column("embedding_max_retries", sa.Integer(), nullable=False),
        sa.Column("chunk_tokens", sa.Integer(), nullable=False),
        sa.Column("chunk_overlap_tokens", sa.Integer(), nullable=False),
        sa.Column("max_upload_mb", sa.Integer(), nullable=False),
        sa.Column("retrieval_top_k", sa.Integer(), nullable=False),
        sa.Column("min_similarity", sa.Float(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("owner_id"),
    )


def downgrade() -> None:
    op.drop_table("workspace_settings")
