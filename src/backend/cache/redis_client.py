"""Redis client construction owned by the application lifecycle."""

from __future__ import annotations

from redis.asyncio import Redis

from ..config import Settings


def create_redis_client(settings: Settings) -> Redis:
    """Create a pooled async Redis client from validated settings."""

    return Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=settings.redis_connect_timeout_seconds,
        socket_timeout=settings.redis_socket_timeout_seconds,
        health_check_interval=settings.redis_health_check_interval_seconds,
    )

