"""SQLAlchemy models.

Importing this package registers every model on ``Base.metadata``, which
is what Alembic autogenerate and the test fixtures rely on.
"""

from app.models.auth import AuthChallenge, AuthSession
from app.models.base import Base
from app.models.conversation import Conversation, Message, MessageCitation, MessageRole
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.evaluation import (
    EvaluationDataset,
    EvaluationDatasetCase,
    EvaluationRun,
    EvaluationRunResult,
)
from app.models.user import User
from app.models.workspace_settings import WorkspaceSettings

__all__ = [
    "Base",
    "Conversation",
    "Document",
    "DocumentChunk",
    "DocumentStatus",
    "EvaluationDataset",
    "EvaluationDatasetCase",
    "EvaluationRun",
    "EvaluationRunResult",
    "Message",
    "MessageCitation",
    "MessageRole",
    "User",
    "AuthChallenge",
    "AuthSession",
    "WorkspaceSettings",
]
