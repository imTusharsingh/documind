"""Shared FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.models.user import User
from app.repositories.users import get_development_owner
from app.services.answers import AnswerProvider, create_answer_provider
from app.services.embeddings import EmbeddingProvider, create_embedding_provider


def get_current_owner(session: Annotated[Session, Depends(get_session)]) -> User:
    """Resolve the acting owner for a request.

    FastAPI caches dependency results per request, so this and any route
    session dependency share one Session instance. When authentication is
    added, only this function changes.
    """
    return get_development_owner(session)


def get_embedding_provider(
    settings: Annotated[Settings, Depends(get_settings)],
) -> EmbeddingProvider:
    """Return the configured embedding provider for a request."""
    return create_embedding_provider(settings)


def get_answer_provider(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AnswerProvider:
    """Return the configured grounded-answer provider for a request."""
    return create_answer_provider(settings)
