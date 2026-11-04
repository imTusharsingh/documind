import uuid

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.user import User

# Fixed so the seeded owner is stable across databases and test runs.
DEVELOPMENT_OWNER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class MissingOwnerError(AppError):
    status_code = 500
    code = "DEVELOPMENT_OWNER_MISSING"
    message = "The development owner is missing. Run `alembic upgrade head`."


def get_development_owner(session: Session) -> User:
    """Return the single seeded owner used by the unauthenticated MVP.

    When authentication arrives this function is replaced by a lookup of
    the authenticated principal; callers keep the same shape.
    """
    owner = session.get(User, DEVELOPMENT_OWNER_ID)
    if owner is None:
        raise MissingOwnerError()
    return owner
