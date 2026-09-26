"""Generic cache storage; no financial models belong here."""

import time
from typing import Protocol

from redis.exceptions import RedisError
from redis.asyncio import Redis

from ..exceptions.cache import CacheUnavailable


class CacheStore(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, ttl_seconds: int) -> None: ...


class RedisCache:
    def __init__(self, client: Redis) -> None:
        self.client = client

    async def get(self, key: str) -> str | None:
        try:
            return await self.client.get(key)
        except RedisError as exc:
            raise CacheUnavailable(
                "Cache unavailable; paid upstream calls disabled."
            ) from exc

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        try:
            await self.client.set(key, value, ex=ttl_seconds)
        except RedisError as exc:
            raise CacheUnavailable(
                "Could not persist upstream response in cache."
            ) from exc


class MemoryCache:
    """Expiring test double; not the production cache."""

    def __init__(self) -> None:
        self.values: dict[str, tuple[float, str]] = {}

    async def get(self, key: str) -> str | None:
        cached = self.values.get(key)
        if cached is None:
            return None

        expiry, value = cached
        return value if expiry > time.monotonic() else None

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self.values[key] = (time.monotonic() + ttl_seconds, value)
