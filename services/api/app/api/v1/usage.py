from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_owner
from app.core.db import get_session
from app.models.conversation import Conversation, Message, MessageRole
from app.models.user import User
from app.schemas.usage import UsageEvent, UsageResponse

router = APIRouter()


@router.get("/usage", response_model=UsageResponse)
def read_usage(
    session: Annotated[Session, Depends(get_session)],
    owner: Annotated[User, Depends(get_current_owner)],
    limit: int = Query(default=30, ge=1, le=100),
) -> UsageResponse:
    """Return owner-scoped assistant token usage for the workspace."""
    messages = session.scalars(
        select(Message)
        .join(Message.conversation)
        .where(Conversation.owner_id == owner.id, Message.role == MessageRole.ASSISTANT)
        .order_by(desc(Message.created_at))
        .limit(limit)
    ).all()
    input_tokens = sum(message.input_tokens or 0 for message in messages)
    output_tokens = sum(message.output_tokens or 0 for message in messages)
    events = [
        UsageEvent(
            id=message.id,
            conversation_id=message.conversation_id,
            conversation_title=message.conversation.title,
            input_tokens=message.input_tokens or 0,
            output_tokens=message.output_tokens or 0,
            total_tokens=(message.input_tokens or 0) + (message.output_tokens or 0),
            latency_ms=message.latency_ms,
            created_at=message.created_at,
        )
        for message in messages
    ]
    return UsageResponse(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        request_count=len(events),
        events=events,
    )
