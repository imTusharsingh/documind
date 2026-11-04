"""Add labels and embedding metadata to evaluation runs.

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("evaluation_runs", sa.Column("label", sa.String(length=120), nullable=True))
    op.add_column(
        "evaluation_runs", sa.Column("embedding_model", sa.String(length=120), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("evaluation_runs", "embedding_model")
    op.drop_column("evaluation_runs", "label")
