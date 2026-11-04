from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.workspace_settings import WorkspaceSettings


def get_workspace_settings(session: Session, owner_id, defaults: Settings) -> WorkspaceSettings:
    settings = session.get(WorkspaceSettings, owner_id)
    if settings is None:
        settings = WorkspaceSettings(
            owner_id=owner_id,
            openai_api_key=None,
            llm_model=defaults.llm_model,
            embedding_model=defaults.embedding_model,
            embedding_dim=defaults.embedding_dim,
            embedding_batch_size=defaults.embedding_batch_size,
            embedding_timeout_seconds=defaults.embedding_timeout_seconds,
            embedding_max_retries=defaults.embedding_max_retries,
            chunk_tokens=defaults.chunk_tokens,
            chunk_overlap_tokens=defaults.chunk_overlap_tokens,
            max_upload_mb=defaults.max_upload_mb,
            retrieval_top_k=5,
            min_similarity=0.15,
        )
        session.add(settings)
        session.flush()
    return settings


def apply_workspace_settings(defaults: Settings, workspace: WorkspaceSettings) -> Settings:
    values = {
        "llm_model": workspace.llm_model,
        "embedding_model": workspace.embedding_model,
        "embedding_dim": workspace.embedding_dim,
        "embedding_batch_size": workspace.embedding_batch_size,
        "embedding_timeout_seconds": workspace.embedding_timeout_seconds,
        "embedding_max_retries": workspace.embedding_max_retries,
        "chunk_tokens": workspace.chunk_tokens,
        "chunk_overlap_tokens": workspace.chunk_overlap_tokens,
        "max_upload_mb": workspace.max_upload_mb,
    }
    if workspace.openai_api_key:
        from pydantic import SecretStr

        values["openai_api_key"] = SecretStr(workspace.openai_api_key)
    return defaults.model_copy(update=values)
