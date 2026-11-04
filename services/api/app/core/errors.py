"""Application error types and the handlers that serialize them.

Every API failure uses the same envelope so the frontend can branch on
``error.code`` instead of parsing human-readable messages:

    {"error": {"code": "...", "message": "...", "details": null}}
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.errors import ErrorBody, ErrorResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for expected, handled failures."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.message
        self.details = details
        self.headers = headers
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"
    message = "The requested resource was not found."


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"
    message = "The request conflicts with the current state."


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "SERVICE_UNAVAILABLE"
    message = "A required dependency is unavailable."


class PayloadTooLargeError(AppError):
    status_code = 413
    code = "PAYLOAD_TOO_LARGE"
    message = "The uploaded file is too large."


class UnsupportedMediaTypeError(AppError):
    status_code = 415
    code = "UNSUPPORTED_MEDIA_TYPE"
    message = "The uploaded file type is not supported."


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(error=ErrorBody(code=code, message=message, details=details))
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(payload),
        headers=headers,
    )


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return _error_response(exc.status_code, exc.code, exc.message, exc.details, exc.headers)


async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code_by_status = {
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
    }
    code = code_by_status.get(exc.status_code, "HTTP_ERROR")
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return _error_response(exc.status_code, code, detail, headers=exc.headers)


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return _error_response(
        status_code=422,
        code="VALIDATION_ERROR",
        message="The request payload is invalid.",
        details=jsonable_encoder(exc.errors()),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error while processing %s %s", request.method, request.url.path)
    return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred.")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
