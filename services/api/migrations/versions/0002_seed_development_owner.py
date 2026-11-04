"""Seed the single development owner.

The owner id is fixed so local databases, test databases, and any future
environment agree on who owns seeded data. ON CONFLICT keeps the seed
idempotent, which matters because startup runs migrations every time.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OWNER_ID = "00000000-0000-0000-0000-000000000001"
OWNER_EMAIL = "owner@documind.local"
OWNER_NAME = "Development Owner"


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO users (id, email, display_name)
            VALUES (CAST(:id AS uuid), :email, :display_name)
            ON CONFLICT (id) DO NOTHING
            """
        ).bindparams(
            id=OWNER_ID,
            email=OWNER_EMAIL,
            display_name=OWNER_NAME,
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM users WHERE id = :id").bindparams(id=OWNER_ID))
