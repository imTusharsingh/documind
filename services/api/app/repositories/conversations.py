"""Conversation persistence scoped to the current owner."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFoundError
from app.models.conversation import Conversation, Message, MessageCitation, MessageRole


def get_conversation(
    session: Session, owner_id: uuid.UUID, conversation_id: uuid.UUID
) -> Conversation:
    conversation = session.scalar(
        select(Conversation)
        .where(Conversation.id == conversation_id, Conversation.owner_id == owner_id)
        .options(selectinload(Conversation.messages).selectinload(Message.citations))
    )
    if conversation is None:
        raise NotFoundError("Conversation was not found.")
    return conversation


def list_conversations(session: Session, owner_id: uuid.UUID) -> list[Conversation]:
    return list(
        session.scalars(
            select(Conversation)
            .where(Conversation.owner_id == owner_id)
            .order_by(Conversation.updated_at.desc(), Conversation.id)
        )
    )


def create_conversation(session: Session, owner_id: uuid.UUID, title: str) -> Conversation:
    conversation = Conversation(id=uuid.uuid4(), owner_id=owner_id, title=title[:200])
    session.add(conversation)
    session.flush()
    return conversation


def add_message(
    session: Session,
    conversation: Conversation,
    *,
    role: MessageRole,
    content: str,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    latency_ms: int | None = None,
    citations: Sequence[MessageCitation] = (),
) -> Message:
    message = Message(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        role=role,
        content=content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
    )
    session.add(message)
    session.flush()
    for citation in citations:
        citation.message_id = message.id
        session.add(citation)
    return message
