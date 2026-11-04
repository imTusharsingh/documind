import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_owner
from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.core.errors import PayloadTooLargeError, UnsupportedMediaTypeError
from app.models.document import DocumentStatus
from app.models.user import User
from app.repositories.documents import (
    create_document,
    delete_document,
    get_document,
    list_documents,
)
from app.schemas.document import DocumentResponse
from app.schemas.errors import ErrorResponse
from app.services.storage import (
    InvalidUploadError,
    UploadTooLargeError,
    remove_file,
    safe_filename,
    save_upload,
    storage_path_for,
)

router = APIRouter()

ERROR_RESPONSES = {
    413: {"model": ErrorResponse, "description": "The upload exceeds the size limit."},
    415: {"model": ErrorResponse, "description": "The upload is not a supported PDF."},
}


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF",
    description=(
        "Streams a PDF to durable storage and creates a pending document. "
        "The ingestion worker picks it up and updates its status."
    ),
    responses=ERROR_RESPONSES,
)
async def upload_document(
    file: Annotated[UploadFile, File(description="PDF file to ingest")],
    session: Annotated[Session, Depends(get_session)],
    owner: Annotated[User, Depends(get_current_owner)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentResponse:
    try:
        filename = safe_filename(file.filename)
    except InvalidUploadError as exc:
        raise UnsupportedMediaTypeError(exc.message) from exc

    document_id = uuid.uuid4()
    destination = storage_path_for(settings.upload_dir, document_id)

    try:
        saved = await save_upload(
            file,
            destination,
            max_bytes=settings.max_upload_bytes,
            max_mb=settings.max_upload_mb,
        )
    except InvalidUploadError as exc:
        raise UnsupportedMediaTypeError(exc.message) from exc
    except UploadTooLargeError as exc:
        raise PayloadTooLargeError(str(exc)) from exc

    try:
        document = create_document(
            session,
            document_id=document_id,
            owner_id=owner.id,
            original_filename=filename,
            content_type=file.content_type or "application/pdf",
            size_bytes=saved.size_bytes,
            storage_path=str(saved.path),
        )
    except Exception:
        remove_file(saved.path)
        raise

    return DocumentResponse.model_validate(document)


@router.get(
    "",
    response_model=list[DocumentResponse],
    summary="List documents",
    description="Returns the owner's documents, newest first, optionally filtered by status.",
)
def read_documents(
    session: Annotated[Session, Depends(get_session)],
    owner: Annotated[User, Depends(get_current_owner)],
    document_status: Annotated[DocumentStatus | None, Query(alias="status")] = None,
) -> list[DocumentResponse]:
    documents = list_documents(session, owner.id, document_status)
    return [DocumentResponse.model_validate(document) for document in documents]


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get a document",
    responses={404: {"model": ErrorResponse, "description": "Document not found."}},
)
def read_document(
    document_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    owner: Annotated[User, Depends(get_current_owner)],
) -> DocumentResponse:
    document = get_document(session, owner.id, document_id)
    return DocumentResponse.model_validate(document)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
    description="Removes the database row, its chunks, and the stored PDF.",
    responses={404: {"model": ErrorResponse, "description": "Document not found."}},
)
def remove_document(
    document_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    owner: Annotated[User, Depends(get_current_owner)],
) -> Response:
    document = delete_document(session, owner.id, document_id)
    remove_file(Path(document.storage_path))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
