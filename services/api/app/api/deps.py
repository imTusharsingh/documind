"""Shared FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.models.user import User
from app.repositories.users import get_development_owner


def get_current_owner(session: Annotated[Session, Depends(get_session)]) -> User:
    """Resolve the acting owner for a request.

    FastAPI caches dependency results per request, so this and any route
    session dependency share one Session instance. When authentication is
    added, only this function changes.
    """
    return get_development_owner(session)
