"""Request correlation and safe access logging, separate from app assembly."""

from __future__ import annotations

import logging
from time import perf_counter
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from .exceptions.registry import InternalError, error_response
from .logger import (
    reset_client_ip,
    reset_request_id,
    set_client_ip,
    set_request_id,
)

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = str(uuid4())
        client_ip = request.client.host if request.client else "-"
        request.state.request_id = request_id
        request_id_token = set_request_id(request_id)
        client_ip_token = set_client_ip(client_ip)
        started_at = perf_counter()
        status_code = 500

        try:
            try:
                response = await call_next(request)
                status_code = response.status_code
            except Exception:
                logger.exception(
                    "Unhandled request exception",
                    extra={"method": request.method, "path": request.url.path},
                )
                response = error_response(
                    request, InternalError("An unexpected error occurred.")
                )
        finally:
            if request.url.path != "/health":
                logger.info(
                    "Request completed",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": status_code,
                        "duration_ms": round((perf_counter() - started_at) * 1000, 2),
                    },
                )
            reset_client_ip(client_ip_token)
            reset_request_id(request_id_token)

        response.headers["X-Request-ID"] = request_id
        return response
