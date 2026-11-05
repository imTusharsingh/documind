"""Shared FastAPI dependencies."""

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.models.user import User
from app.repositories.users import get_development_owner
from app.services.auth import user_for_token
from app.services.answers import AnswerProvider, create_answer_provider
from app.services.embeddings import EmbeddingProvider, create_embedding_provider
from app.services.workspace_settings import apply_workspace_settings, get_workspace_settings


def get_current_owner(session: Annotated[Session, Depends(get_session)], documind_session: Annotated[str | None, Cookie()] = None) -> User:
    """Resolve the acting owner for a request.

    FastAPI caches dependency results per request, so this and any route
    session dependency share one Session instance. When authentication is
    added, only this function changes.
    """
    return user_for_token(session, documind_session) or get_development_owner(session)


def get_embedding_provider(
    session: Annotated[Session, Depends(get_session)],
    owner: Annotated[User, Depends(get_current_owner)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EmbeddingProvider:
    """Return the configured embedding provider for a request."""
    workspace = get_workspace_settings(session, owner.id, settings)
    return create_embedding_provider(apply_workspace_settings(settings, workspace))


def get_answer_provider(
    session: Annotated[Session, Depends(get_session)],
    owner: Annotated[User, Depends(get_current_owner)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AnswerProvider:
    """Return the configured grounded-answer provider for a request."""
    workspace = get_workspace_settings(session, owner.id, settings)
    return create_answer_provider(apply_workspace_settings(settings, workspace))
