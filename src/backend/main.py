"""FastAPI application entry point for IntelFlow."""

from __future__ import annotations

import logging
import asyncio
import os
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from redis.exceptions import RedisError

from .cache import create_redis_client
from .config import get_settings
from .logger import configure_logging, reset_request_id, set_request_id
from .api.routes import router
from .cache.store import RedisCache
from .exceptions.cache import CacheUnavailable
from .exceptions.research import ResearchError
from .exceptions.sectors import (
    SectorsAuthenticationError,
    SectorsConfigurationError,
    SectorsError,
    SectorsNotFoundError,
    SectorsRateLimitError,
    SectorsUpstreamError,
    SectorsValidationError,
)
from .sectors.cached import CachedSectorsGateway
from .sectors.client import SectorsClient
from .services.research import ResearchService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Own shared backend dependencies for the application process."""

    if application.state.injected_service:
        yield
        return
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

    client = None
    try:
        client = SectorsClient()
        application.state.settings = settings
        application.state.redis = redis_client
        application.state.research = ResearchService(
            CachedSectorsGateway(client, RedisCache(redis_client), settings)
        )
        logger.info("Research dependencies ready")
        yield
    finally:
        if client:
            await asyncio.to_thread(client.close)
        await redis_client.aclose()
        logger.info("Redis connection closed")


def create_app(*, service: ResearchService | None = None) -> FastAPI:
    """Create and configure the IntelFlow API application."""

    configure_logging()

    application = FastAPI(
        title="IntelFlow API",
        description="Flow-first market intelligence for IDX stocks.",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.injected_service = service is not None
    if service:
        application.state.research = service
    application.include_router(router)
    origins = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if o.strip()
    ]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    @application.middleware("http")
    async def log_request(request: Request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id
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
            response = JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred.",
                        "request_id": request_id,
                    }
                },
            )
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
            content={
                "error": {
                    "code": error_code,
                    "message": str(exc),
                    "request_id": _request.state.request_id,
                }
            },
        )

    @application.exception_handler(ResearchError)
    async def research_error(request: Request, exc: ResearchError):
        return JSONResponse(
            status_code=exc.status,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": request.state.request_id,
                }
            },
        )

    @application.exception_handler(CacheUnavailable)
    async def cache_error(request: Request, exc: CacheUnavailable):
        logger.error(
            "Cache unavailable; request stopped",
            extra={"error_type": type(exc).__name__},
        )
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "CACHE_UNAVAILABLE",
                    "message": str(exc),
                    "request_id": request.state.request_id,
                }
            },
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "Invalid query or path parameters; consult /docs.",
                    "request_id": request.state.request_id,
                }
            },
        )

    @application.get("/health", tags=["system"])
    async def health():
        if application.state.injected_service:
            return {"status": "healthy", "dependencies": {"redis": "test-double"}}
        try:
            await application.state.redis.ping()
        except RedisError:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "dependencies": {"redis": "unavailable"},
                },
            )
        return {"status": "healthy", "dependencies": {"redis": "healthy"}}

    return application


def _map_sectors_error(exc: SectorsError) -> tuple[int, str]:
    if isinstance(exc, SectorsConfigurationError):
        return 503, "UPSTREAM_CONFIGURATION_ERROR"
    if isinstance(exc, SectorsValidationError):
        return 503, "UPSTREAM_REQUEST_REJECTED"
    if isinstance(exc, SectorsAuthenticationError):
        return 503, "UPSTREAM_AUTHENTICATION_ERROR"
    if isinstance(exc, SectorsNotFoundError):
        return 404, "DATA_NOT_FOUND"
    if isinstance(exc, SectorsRateLimitError):
        return 503, "UPSTREAM_RATE_LIMIT"
    if isinstance(exc, SectorsUpstreamError):
        return 503, "UPSTREAM_UNAVAILABLE"
    return 503, "UPSTREAM_INVALID_RESPONSE"


app = create_app()
