import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentStatus


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    content_type: str
    size_bytes: int
    status: DocumentStatus
    page_count: int | None
    chunk_count: int | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
