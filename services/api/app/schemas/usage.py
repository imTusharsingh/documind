import uuid
from datetime import datetime

from pydantic import BaseModel


class UsageEvent(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    conversation_title: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: int | None
    created_at: datetime


class UsageResponse(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    request_count: int
    events: list[UsageEvent]
