"""Add evaluation regression thresholds and report status.

Revision ID: 0008
Revises: 0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "evaluation_datasets", sa.Column("minimum_recall_at_k", sa.Float(), nullable=True)
    )
    op.add_column("evaluation_datasets", sa.Column("minimum_mrr", sa.Float(), nullable=True))
    op.add_column(
        "evaluation_datasets", sa.Column("minimum_page_match_rate", sa.Float(), nullable=True)
    )
    op.add_column("evaluation_runs", sa.Column("regression_passed", sa.Boolean(), nullable=True))
    op.add_column("evaluation_runs", sa.Column("regression_failures", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("evaluation_runs", "regression_failures")
    op.drop_column("evaluation_runs", "regression_passed")
    op.drop_column("evaluation_datasets", "minimum_page_match_rate")
    op.drop_column("evaluation_datasets", "minimum_mrr")
    op.drop_column("evaluation_datasets", "minimum_recall_at_k")
