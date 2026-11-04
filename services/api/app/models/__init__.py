"""SQLAlchemy models.

Importing this package registers every model on ``Base.metadata``, which
is what Alembic autogenerate and the test fixtures rely on.
"""

from app.models.base import Base
from app.models.conversation import Conversation, Message, MessageCitation, MessageRole
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.user import User

__all__ = [
    "Base",
    "Conversation",
    "Document",
    "DocumentChunk",
    "DocumentStatus",
    "Message",
    "MessageCitation",
    "MessageRole",
    "User",
]
