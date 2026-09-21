"""FastAPI application entry point for IntelFlow."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError

from .cache import create_redis_client
from .config import get_settings
from .logger import configure_logging, reset_request_id, set_request_id
from .sectors.exceptions import (
    SectorsAuthenticationError,
    SectorsConfigurationError,
    SectorsError,
    SectorsNotFoundError,
    SectorsRateLimitError,
    SectorsUpstreamError,
    SectorsValidationError,
)


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Own shared backend dependencies for the application process."""

    settings = get_settings()
    redis_client = create_redis_client(settings)

    try:
        await redis_client.ping()
    except RedisError as exc:
        await redis_client.aclose()
        logger.exception("Redis startup check failed")
        raise RuntimeError(
            "Redis is required. Start it with `docker compose up -d redis`."
        ) from exc

    application.state.settings = settings
    application.state.redis = redis_client
    logger.info("Redis connection ready")

    try:
        yield
    finally:
        await redis_client.aclose()
        logger.info("Redis connection closed")


def create_app() -> FastAPI:
    """Create and configure the IntelFlow API application."""

    configure_logging()

    application = FastAPI(
        title="IntelFlow API",
        description="Flow-first market intelligence for IDX stocks.",
        version="0.1.0",
        lifespan=lifespan,
    )

    @application.middleware("http")
    async def log_request(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        token = set_request_id(request_id)
        started_at = perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            logger.exception(
                "Unhandled request exception",
                extra={"method": request.method, "path": request.url.path},
            )
            raise
        finally:
            duration_ms = (perf_counter() - started_at) * 1000
            logger.info(
                "Request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            reset_request_id(token)

        response.headers["X-Request-ID"] = request_id
        return response

    @application.exception_handler(SectorsError)
    async def handle_sectors_error(
        _request: Request,
        exc: SectorsError,
    ) -> JSONResponse:
        status_code, error_code = _map_sectors_error(exc)
        logger.warning(
            "Sectors request could not be completed",
            extra={
                "error_code": error_code,
                "upstream_status": exc.status_code,
            },
        )
        return JSONResponse(
            status_code=status_code,
            content={"error": error_code, "message": str(exc)},
        )

    @application.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "intelflow-api"}

    return application


def _map_sectors_error(exc: SectorsError) -> tuple[int, str]:
    if isinstance(exc, SectorsConfigurationError):
        return 500, "sectors_configuration_error"
    if isinstance(exc, SectorsValidationError):
        return 400, "sectors_validation_error"
    if isinstance(exc, SectorsAuthenticationError):
        return 502, "sectors_authentication_error"
    if isinstance(exc, SectorsNotFoundError):
        return 404, "sectors_data_not_found"
    if isinstance(exc, SectorsRateLimitError):
        return 503, "sectors_rate_limit_error"
    if isinstance(exc, SectorsUpstreamError):
        return 502, "sectors_upstream_error"
    return 502, "sectors_error"


app = create_app()
