import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DocumentStatus(enum.StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


document_status_type = Enum(
    DocumentStatus,
    name="document_status",
    native_enum=False,
    length=20,
    validate_strings=True,
    values_callable=lambda statuses: [status.value for status in statuses],
)


class Document(Base):
    """An uploaded PDF and its ingestion state.

    ``page_count`` and ``chunk_count`` are written once, in the same
    transaction that marks the document ready, so they never describe a
    partially ingested document.
    """

    __tablename__ = "documents"
    __table_args__ = (Index("ix_documents_status_created_at", "status", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    storage_path: Mapped[str] = mapped_column(String(500))

    status: Mapped[DocumentStatus] = mapped_column(
        document_status_type,
        default=DocumentStatus.PENDING,
    )
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class DocumentChunk(Base):
    """One retrievable passage of a document.

    Chunks never cross a page boundary, so a citation can always name a
    single page. ``chunk_index`` is sequential across the document and
    ``token_count`` uses the same tokenizer family as the embedding model.
    """

    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_document_chunks_document_id_chunk_index",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    document: Mapped[Document] = relationship(back_populates="chunks")
