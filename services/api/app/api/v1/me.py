from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_owner
from app.models.user import User
from app.schemas.errors import ErrorResponse
from app.schemas.user import OwnerResponse

router = APIRouter()


@router.get(
    "/me",
    response_model=OwnerResponse,
    summary="Current owner",
    description="Returns the authenticated workspace member.",
    responses={500: {"model": ErrorResponse, "description": "The owner is missing."}},
)
def read_current_owner(owner: Annotated[User, Depends(get_current_owner)]) -> OwnerResponse:
    return OwnerResponse.model_validate(owner)
