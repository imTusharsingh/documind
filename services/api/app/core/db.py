"""Database engine, session factory, and the FastAPI session dependency."""

from collections.abc import Iterator
from time import perf_counter

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.schemas.health import DependencyStatus

settings = get_settings()

engine = create_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    connect_args={"connect_timeout": settings.db_connect_timeout},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def get_session() -> Iterator[Session]:
    """Yield a request-scoped session and always return the connection.

    Routes in this project do not commit implicitly. Services and
    repositories decide their own transaction boundaries, and the
    session is rolled back if an exception escapes the request.
    """
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_database(session: Session) -> DependencyStatus:
    """Run a trivial query so readiness reflects real connectivity.

    Failures are reported as data rather than raised, because a health
    endpoint must answer with a body even when the database is down.
    """
    started = perf_counter()
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return DependencyStatus(
            status="down",
            error="Database connection failed.",
        )

    return DependencyStatus(
        status="up",
        latency_ms=round((perf_counter() - started) * 1000, 2),
    )
