from typing import Literal

from pydantic import BaseModel


class DependencyStatus(BaseModel):
    """Readiness of one external dependency."""

    status: Literal["up", "down"]
    latency_ms: float | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    service: str
    version: str
    environment: str
    dependencies: dict[str, DependencyStatus]
