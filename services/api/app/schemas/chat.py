import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: uuid.UUID | None = None
    document_ids: list[uuid.UUID] = Field(default_factory=list, max_length=50)
    top_k: int = Field(default=5, ge=1, le=12)
    min_similarity: float = Field(default=0.15, ge=0.0, le=1.0)


class Citation(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    page_number: int
    chunk_index: int
    quote: str


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    answer: str
    citations: list[Citation]
    insufficient_evidence: bool


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationMessage(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime
    citations: list[Citation]


class ConversationResponse(ConversationSummary):
    messages: list[ConversationMessage]
