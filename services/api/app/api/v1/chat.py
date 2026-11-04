import logging
import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_answer_provider, get_current_owner, get_embedding_provider
from app.core.db import get_session
from app.core.errors import AnswerUnavailableError, EmbeddingUnavailableError
from app.models.conversation import MessageCitation, MessageRole
from app.models.user import User
from app.repositories.conversations import (
    add_message,
    create_conversation,
    get_conversation,
    list_conversations,
)
from app.repositories.search import search_chunks
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    Citation,
    ConversationMessage,
    ConversationResponse,
    ConversationSummary,
)
from app.services.answers import AnswerProvider, AnswerProviderError
from app.services.embeddings import (
    EmbeddingConfigurationError,
    EmbeddingProvider,
    EmbeddingProviderError,
)

logger = logging.getLogger(__name__)
router = APIRouter()
INSUFFICIENT_EVIDENCE = "I couldn't find enough evidence in your documents to answer that."


def _citation_response(hit) -> Citation:
    return Citation(
        chunk_id=hit.chunk_id,
        document_id=hit.document_id,
        document_name=hit.document_name,
        page_number=hit.page_number,
        chunk_index=hit.chunk_index,
        quote=hit.content,
    )


def _conversation_response(conversation) -> ConversationResponse:
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            ConversationMessage(
                id=message.id,
                role=message.role.value,
                content=message.content,
                created_at=message.created_at,
                citations=[
                    Citation(
                        chunk_id=citation.chunk_id,
                        document_id=citation.document_id,
                        document_name=citation.document_name,
                        page_number=citation.page_number,
                        chunk_index=citation.chunk_index,
                        quote=citation.quote,
                    )
                    for citation in message.citations
                ],
            )
            for message in conversation.messages
        ],
    )


@router.get("/conversations", response_model=list[ConversationSummary])
def read_conversations(
    session: Annotated[Session, Depends(get_session)],
    owner: Annotated[User, Depends(get_current_owner)],
) -> list[ConversationSummary]:
    return [
        ConversationSummary.model_validate(item) for item in list_conversations(session, owner.id)
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def read_conversation(
    conversation_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    owner: Annotated[User, Depends(get_current_owner)],
) -> ConversationResponse:
    return _conversation_response(get_conversation(session, owner.id, conversation_id))


@router.post("/chat", response_model=ChatResponse, status_code=200)
def chat(
    request: ChatRequest,
    session: Annotated[Session, Depends(get_session)],
    owner: Annotated[User, Depends(get_current_owner)],
    embedding_provider: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
    answer_provider: Annotated[AnswerProvider, Depends(get_answer_provider)],
) -> ChatResponse:
    started = time.perf_counter()
    conversation = (
        get_conversation(session, owner.id, request.conversation_id)
        if request.conversation_id
        else create_conversation(session, owner.id, request.question)
    )
    history = [(message.role.value, message.content) for message in conversation.messages[-10:]]
    add_message(session, conversation, role=MessageRole.USER, content=request.question)

    try:
        vectors = embedding_provider.embed_texts([request.question])
        if len(vectors) != 1:
            raise EmbeddingProviderError("The embedding provider returned no query vector.")
        hits = search_chunks(
            session,
            owner_id=owner.id,
            query_embedding=vectors[0],
            limit=request.top_k,
            document_ids=request.document_ids,
            min_similarity=request.min_similarity,
        )
    except (EmbeddingConfigurationError, EmbeddingProviderError) as exc:
        session.rollback()
        raise EmbeddingUnavailableError(str(exc)) from exc

    valid_hits = {str(hit.chunk_id): hit for hit in hits}
    citations: list[Citation] = []
    answer = INSUFFICIENT_EVIDENCE
    input_tokens = output_tokens = None

    if hits:
        try:
            generated = answer_provider.answer(request.question, hits, history)
        except AnswerProviderError as exc:
            session.rollback()
            logger.warning("Grounded answer failed: %s", exc)
            raise AnswerUnavailableError(str(exc)) from exc

        cited_hits = []
        for chunk_id in generated.citation_chunk_ids:
            hit = valid_hits.get(chunk_id)
            if hit is not None and hit not in cited_hits:
                cited_hits.append(hit)
        if cited_hits and generated.answer.strip():
            answer = generated.answer.strip()
            citations = [_citation_response(hit) for hit in cited_hits]
        input_tokens = generated.input_tokens
        output_tokens = generated.output_tokens

    citation_rows = [
        MessageCitation(
            id=uuid.uuid4(),
            chunk_id=citation.chunk_id,
            document_id=citation.document_id,
            document_name=citation.document_name,
            page_number=citation.page_number,
            chunk_index=citation.chunk_index,
            quote=citation.quote,
        )
        for citation in citations
    ]
    message = add_message(
        session,
        conversation,
        role=MessageRole.ASSISTANT,
        content=answer,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=round((time.perf_counter() - started) * 1000),
        citations=citation_rows,
    )
    session.commit()
    return ChatResponse(
        conversation_id=conversation.id,
        message_id=message.id,
        answer=answer,
        citations=citations,
        insufficient_evidence=not citations,
    )
