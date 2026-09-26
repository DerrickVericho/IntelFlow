"""One registration point for public HTTP error responses."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .base import AppError
from .cache import CacheUnavailable
from .sectors import SectorsError

logger = logging.getLogger(__name__)


def error_response(request: Request, error: AppError) -> JSONResponse:
    """Serialize only the safe public error contract, never provider details."""

    request_id = getattr(request.state, "request_id", "-")
    if isinstance(error, SectorsError):
        message = {
            "DATA_NOT_FOUND": "Sectors data was not found.",
            "UPSTREAM_RATE_LIMIT": "Sectors API rate or credit limit was reached.",
            "UPSTREAM_AUTHENTICATION_ERROR": "Sectors API authentication failed.",
            "UPSTREAM_CONFIGURATION_ERROR": "Sectors API is not configured.",
            "UPSTREAM_REQUEST_REJECTED": "Sectors API rejected the request.",
            "UPSTREAM_UNAVAILABLE": "Sectors API is unavailable.",
            "UPSTREAM_INVALID_RESPONSE": "Sectors API returned an invalid response.",
        }.get(error.code, "Sectors API request failed.")
    elif isinstance(error, CacheUnavailable):
        message = "Cache unavailable; request could not be completed."
    else:
        message = error.message
    return JSONResponse(
        status_code=error.http_status,
        content={
            "error": {
                "code": error.code,
                "message": message,
                "request_id": request_id,
            }
        },
        headers={"X-Request-ID": request_id},
    )


async def app_error_handler(request: Request, error: AppError) -> JSONResponse:
    extra = {"error_code": error.code, "error_type": type(error).__name__}
    if isinstance(error, SectorsError):
        extra["upstream_status"] = error.status_code
    logger.warning("Application request failed", extra=extra)
    return error_response(request, error)


async def validation_error_handler(
    request: Request, _error: RequestValidationError
) -> JSONResponse:
    # FastAPI validation details can contain user input, so keep the response safe.
    error = InvalidRequestError("Invalid query or path parameters; consult /docs.")
    logger.warning("Request validation failed", extra={"error_code": error.code})
    return error_response(request, error)


class InvalidRequestError(AppError):
    code = "INVALID_REQUEST"
    http_status = 422


class InternalError(AppError):
    code = "INTERNAL_ERROR"
    http_status = 500


EXCEPTION_REGISTRY = {
    AppError: app_error_handler,
    RequestValidationError: validation_error_handler,
}


def register_exception_handlers(application: FastAPI) -> None:
    for error_type, handler in EXCEPTION_REGISTRY.items():
        application.add_exception_handler(error_type, handler)
