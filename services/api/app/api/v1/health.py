from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import check_database, get_session
from app.schemas.errors import ErrorResponse
from app.schemas.health import HealthResponse

router = APIRouter()

ERROR_RESPONSES = {
    503: {"model": ErrorResponse, "description": "A dependency is unavailable."},
}


@router.get(
    "/health/live",
    response_model=HealthResponse,
    summary="Liveness probe",
    description=(
        "Reports that the process is running. It intentionally checks no "
        "dependencies, so an orchestrator can distinguish a dead process "
        "from a degraded one."
    ),
)
def liveness(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.version,
        environment=settings.environment,
        dependencies={},
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Readiness probe",
    description=(
        "Reports whether the API can serve requests, including database "
        "connectivity. Returns 503 when a dependency is down."
    ),
    responses=ERROR_RESPONSES,
)
def readiness(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[Session, Depends(get_session)],
) -> HealthResponse:
    database = check_database(session)
    status = "ok" if database.status == "up" else "degraded"

    if status == "degraded":
        response.status_code = 503

    return HealthResponse(
        status=status,
        service=settings.app_name,
        version=settings.version,
        environment=settings.environment,
        dependencies={"database": database},
    )
