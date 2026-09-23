"""FastAPI application assembly and dependency lifespan for IntelFlow."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError

from .api.routes import router
from .cache import create_redis_client
from .cache.store import RedisCache
from .config import get_settings
from .exceptions.registry import register_exception_handlers
from .logger import configure_logging
from .middleware import RequestLoggingMiddleware
from .sectors.cached import CachedSectorsGateway
from .sectors.client import SectorsClient
from .services.research import ResearchService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Own Redis and Sectors transport for a single application worker."""

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
    """Create the API with a single exception registry and request middleware."""

    configure_logging()
    application = FastAPI(
        title="IntelFlow API",
        description="Flow-first market intelligence for IDX stocks.",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.injected_service = service is not None
    if service is not None:
        application.state.research = service

    application.include_router(router)
    register_exception_handlers(application)

    origins = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    application.add_middleware(RequestLoggingMiddleware)

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


app = create_app()
