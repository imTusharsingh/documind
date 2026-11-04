from datetime import datetime

from pydantic import BaseModel, Field


class WorkspaceSettingsResponse(BaseModel):
    api_key_configured: bool
    api_key_hint: str | None
    llm_model: str
    embedding_model: str
    embedding_dim: int
    embedding_batch_size: int
    embedding_timeout_seconds: float
    embedding_max_retries: int
    chunk_tokens: int
    chunk_overlap_tokens: int
    max_upload_mb: int
    retrieval_top_k: int
    min_similarity: float
    updated_at: datetime | None


class WorkspaceSettingsUpdate(BaseModel):
    openai_api_key: str | None = Field(default=None, max_length=500)
    llm_model: str | None = Field(default=None, min_length=1, max_length=200)
    embedding_model: str | None = Field(default=None, min_length=1, max_length=200)
    embedding_dim: int | None = Field(default=None, ge=1, le=8192)
    embedding_batch_size: int | None = Field(default=None, ge=1, le=2048)
    embedding_timeout_seconds: float | None = Field(default=None, gt=0, le=300)
    embedding_max_retries: int | None = Field(default=None, ge=0, le=10)
    chunk_tokens: int | None = Field(default=None, ge=32, le=8192)
    chunk_overlap_tokens: int | None = Field(default=None, ge=0, le=4096)
    max_upload_mb: int | None = Field(default=None, ge=1, le=1024)
    retrieval_top_k: int | None = Field(default=None, ge=1, le=12)
    min_similarity: float | None = Field(default=None, ge=0, le=1)
