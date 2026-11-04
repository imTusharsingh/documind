from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_owner
from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.models.user import User
from app.schemas.settings import WorkspaceSettingsResponse, WorkspaceSettingsUpdate
from app.services.workspace_settings import get_workspace_settings

router = APIRouter()


def _response(settings) -> WorkspaceSettingsResponse:
    key = settings.openai_api_key
    return WorkspaceSettingsResponse(
        api_key_configured=bool(key),
        api_key_hint=f"{key[:4]}…{key[-4:]}" if key and len(key) > 8 else None,
        llm_model=settings.llm_model,
        embedding_model=settings.embedding_model,
        embedding_dim=settings.embedding_dim,
        embedding_batch_size=settings.embedding_batch_size,
        embedding_timeout_seconds=settings.embedding_timeout_seconds,
        embedding_max_retries=settings.embedding_max_retries,
        chunk_tokens=settings.chunk_tokens,
        chunk_overlap_tokens=settings.chunk_overlap_tokens,
        max_upload_mb=settings.max_upload_mb,
        retrieval_top_k=settings.retrieval_top_k,
        min_similarity=settings.min_similarity,
        updated_at=settings.updated_at,
    )


@router.get("/settings", response_model=WorkspaceSettingsResponse)
def read_settings(
    session: Annotated[Session, Depends(get_session)],
    owner: Annotated[User, Depends(get_current_owner)],
    defaults: Annotated[Settings, Depends(get_settings)],
) -> WorkspaceSettingsResponse:
    return _response(get_workspace_settings(session, owner.id, defaults))


@router.patch("/settings", response_model=WorkspaceSettingsResponse)
def update_settings(
    request: WorkspaceSettingsUpdate,
    session: Annotated[Session, Depends(get_session)],
    owner: Annotated[User, Depends(get_current_owner)],
    defaults: Annotated[Settings, Depends(get_settings)],
) -> WorkspaceSettingsResponse:
    settings = get_workspace_settings(session, owner.id, defaults)
    for field, value in request.model_dump(exclude_unset=True).items():
        if field == "openai_api_key" and value == "":
            value = None
        setattr(settings, field, value)
    session.commit()
    session.refresh(settings)
    return _response(settings)


@router.post("/settings/reset", response_model=WorkspaceSettingsResponse)
def reset_settings(
    session: Annotated[Session, Depends(get_session)],
    owner: Annotated[User, Depends(get_current_owner)],
    defaults: Annotated[Settings, Depends(get_settings)],
) -> WorkspaceSettingsResponse:
    settings = get_workspace_settings(session, owner.id, defaults)
    settings.openai_api_key = None
    settings.llm_model = defaults.llm_model
    settings.embedding_model = defaults.embedding_model
    settings.embedding_dim = defaults.embedding_dim
    settings.embedding_batch_size = defaults.embedding_batch_size
    settings.embedding_timeout_seconds = defaults.embedding_timeout_seconds
    settings.embedding_max_retries = defaults.embedding_max_retries
    settings.chunk_tokens = defaults.chunk_tokens
    settings.chunk_overlap_tokens = defaults.chunk_overlap_tokens
    settings.max_upload_mb = defaults.max_upload_mb
    settings.retrieval_top_k = 5
    settings.min_similarity = 0.15
    session.commit()
    session.refresh(settings)
    return _response(settings)
