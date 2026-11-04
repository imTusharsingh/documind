"""Test fixtures backed by a real PostgreSQL database.

These tests intentionally use PostgreSQL instead of SQLite: the schema
relies on native UUIDs, timezone-aware timestamps, and pgvector. Testing
against a substitute would verify behaviour the application never sees.

The fixture creates ``documind_test`` if needed, runs Alembic to head
once per session, and then wraps every test in a transaction that is
rolled back afterwards so tests cannot leak state into each other.
"""

import hashlib
import math
import os
import re
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path

import pymupdf
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

from app.api.deps import get_answer_provider, get_embedding_provider  # noqa: E402
from app.core.config import Settings, get_settings  # noqa: E402
from app.core.db import get_session  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.answers import AnswerProvider, GeneratedAnswer  # noqa: E402
from app.services.embeddings import EmbeddingProvider  # noqa: E402


class DeterministicEmbeddingProvider(EmbeddingProvider):
    """Test provider that turns tokens into stable signed-hash vectors.

    It is intentionally not a language model: shared tokens produce
    similarity, which is enough to exercise storage, SQL ranking, filters,
    and citation plumbing without any network dependency.
    """

    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions
        self.calls: list[list[str]] = []

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [self._vector(text) for text in texts]

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            vector[index] += 1.0 if digest[4] % 2 == 0 else -1.0

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            vector[0] = 1.0
            return vector

        return [value / norm for value in vector]


class DeterministicAnswerProvider(AnswerProvider):
    """Test answer provider that cites the highest-ranked passage."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str]]] = []

    def answer(self, question, passages, history) -> GeneratedAnswer:
        self.calls.append((question, [str(passage.chunk_id) for passage in passages]))
        return GeneratedAnswer(
            answer=f"The documents support this answer to: {question}",
            citation_chunk_ids=[str(passages[0].chunk_id)],
            input_tokens=10,
            output_tokens=8,
        )


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
def test_settings(tmp_path: Path) -> Settings:
    """Settings pointed at a throwaway upload directory.

    The size limit is lowered to 1 MB so the rejection path can be tested
    without generating a large document.
    """
    return get_settings().model_copy(
        update={
            "upload_dir": str(tmp_path / "uploads"),
            "max_upload_mb": 1,
        }
    )


@pytest.fixture
def fake_embedder() -> DeterministicEmbeddingProvider:
    return DeterministicEmbeddingProvider(dimensions=1536)


@pytest.fixture
def fake_answer_provider() -> DeterministicAnswerProvider:
    return DeterministicAnswerProvider()


@pytest.fixture
def client(
    session: Session,
    test_settings: Settings,
    fake_embedder: DeterministicEmbeddingProvider,
    fake_answer_provider: DeterministicAnswerProvider,
) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_embedding_provider] = lambda: fake_embedder
    app.dependency_overrides[get_answer_provider] = lambda: fake_answer_provider

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def pdf_factory() -> Callable[[Path, list[str]], Path]:
    """Create a real PDF with one page per provided string."""

    def _make(path: Path, pages: list[str]) -> Path:
        document = pymupdf.open()
        for body in pages:
            page = document.new_page()
            if body:
                page.insert_textbox(
                    pymupdf.Rect(72, 72, 523, 770),
                    body,
                    fontsize=11,
                )
        document.save(path)
        document.close()
        return path

    return _make
