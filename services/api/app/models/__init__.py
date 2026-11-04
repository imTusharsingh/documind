"""SQLAlchemy models.

Importing this package registers every model on ``Base.metadata``, which
is what Alembic autogenerate and the test fixtures rely on.
"""

from app.models.base import Base
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.user import User

__all__ = ["Base", "Document", "DocumentChunk", "DocumentStatus", "User"]
