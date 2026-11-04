import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WorkspaceSettings(Base):
    __tablename__ = "workspace_settings"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    openai_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_model: Mapped[str] = mapped_column(Text)
    embedding_model: Mapped[str] = mapped_column(Text)
    embedding_dim: Mapped[int] = mapped_column(Integer)
    embedding_batch_size: Mapped[int] = mapped_column(Integer)
    embedding_timeout_seconds: Mapped[float] = mapped_column(Float)
    embedding_max_retries: Mapped[int] = mapped_column(Integer)
    chunk_tokens: Mapped[int] = mapped_column(Integer)
    chunk_overlap_tokens: Mapped[int] = mapped_column(Integer)
    max_upload_mb: Mapped[int] = mapped_column(Integer)
    retrieval_top_k: Mapped[int] = mapped_column(Integer)
    min_similarity: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
