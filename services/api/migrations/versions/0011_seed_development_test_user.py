"""Seed the development authentication test user."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import insert

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    users = sa.table(
        "users",
        sa.column("id", sa.Uuid()),
        sa.column("email", sa.String()),
        sa.column("display_name", sa.String()),
        sa.column("password_hash", sa.String()),
    )
    op.execute(
        insert(users)
        .values(
            id="00000000-0000-0000-0000-000000000002",
            email="tushar.singh+test@documind.com",
            display_name="Tushar Singh (Test)",
            password_hash="scrypt$00112233445566778899aabbccddeeff$848a78a0636b12d2d9308970c1379c41f76f8b1b4c096b5f8d8be8145879917cf994ac329366068f20f202aa9b71dc2ca70166cdaab7d0bb038f49ca36ee1cb0",
        )
        .on_conflict_do_nothing(index_elements=["email"])
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM users WHERE email = :email").bindparams(
            email="tushar.singh+test@documind.com"
        )
    )
