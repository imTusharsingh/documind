from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.repositories.users import get_development_owner
from app.schemas.errors import ErrorResponse
from app.schemas.user import OwnerResponse

router = APIRouter()


@router.get(
    "/me",
    response_model=OwnerResponse,
    summary="Current owner",
    description=(
        "Returns the workspace owner. Until authentication exists this is "
        "the single seeded development owner."
    ),
    responses={500: {"model": ErrorResponse, "description": "The owner is missing."}},
)
def read_current_owner(session: Annotated[Session, Depends(get_session)]) -> OwnerResponse:
    owner = get_development_owner(session)
    return OwnerResponse.model_validate(owner)
