"""Test fixtures backed by a real PostgreSQL database.

These tests intentionally use PostgreSQL instead of SQLite: the schema
relies on native UUIDs, timezone-aware timestamps, and pgvector. Testing
against a substitute would verify behaviour the application never sees.

The fixture creates ``documind_test`` if needed, runs Alembic to head
once per session, and then wraps every test in a transaction that is
rolled back afterwards so tests cannot leak state into each other.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

API_DIR = Path(__file__).resolve().parents[1]

DEFAULT_TEST_DATABASE_URL = (
    "postgresql+psycopg://documind:documind_dev_password@localhost:5432/documind_test"
)

# The application reads DATABASE_URL through Pydantic settings at import
# time, so this must happen before any app module is imported.
TEST_DATABASE_URL = os.environ.setdefault(
    "DATABASE_URL", os.getenv("DOCUMIND_TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
)

from app.core.db import get_session  # noqa: E402
from app.main import create_app  # noqa: E402


def _quote(identifier: str) -> str:
    """Quote a PostgreSQL identifier for the CREATE DATABASE statement."""
    return '"' + identifier.replace('"', '""') + '"'


def _ensure_database(url: str) -> None:
    parsed = make_url(url)
    if parsed.database is None:
        raise RuntimeError("The test database URL must include a database name.")

    admin_engine = create_engine(
        parsed.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )
    try:
        with admin_engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": parsed.database},
            ).scalar()
            if not exists:
                connection.execute(text(f"CREATE DATABASE {_quote(parsed.database)}"))
    finally:
        admin_engine.dispose()


def _run_migrations(url: str) -> None:
    config = Config(str(API_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(API_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(config, "head")


@pytest.fixture(scope="session")
def database_url() -> str:
    _ensure_database(TEST_DATABASE_URL)
    _run_migrations(TEST_DATABASE_URL)
    return TEST_DATABASE_URL


@pytest.fixture(scope="session")
def engine(database_url: str) -> Iterator[Engine]:
    engine = create_engine(database_url, poolclass=NullPool)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    db_session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    try:
        yield db_session
    finally:
        db_session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
