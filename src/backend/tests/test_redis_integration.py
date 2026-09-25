"""Opt-in integration test. Uses unique keys and deletes only its own keys."""

import asyncio
import os
from dataclasses import replace
from uuid import uuid4

import pytest
from redis.asyncio import Redis

from src.backend.cache.store import RedisCache
from src.backend.config import Settings
from src.backend.sectors.cached import CachedSectorsGateway
from src.backend.sectors.utils import canonical_key
from src.backend.tests.fixtures import FixtureTransport, TODAY


@pytest.mark.skipif(
    os.getenv("TEST_REDIS_URL") is None,
    reason="Set TEST_REDIS_URL to run real Redis integration",
)
def test_cache_survives_gateway_recreation():
    async def scenario():
        client = Redis.from_url(os.environ["TEST_REDIS_URL"], decode_responses=True)
        prefix = "intelflow:test:" + uuid4().hex
        settings = replace(Settings.from_env(), redis_key_prefix=prefix)
        params = {"start": "2026-09-01", "end": TODAY.isoformat()}
        key = canonical_key(prefix, "get_daily", "TEST", params)
        transport = FixtureTransport()
        try:
            await client.ping()
            first = CachedSectorsGateway(transport, RedisCache(client), settings)
            a = await first.get_daily("TEST", **params)
            second = CachedSectorsGateway(transport, RedisCache(client), settings)
            b = await second.get_daily("TEST", **params)
            assert a == b
            assert transport.calls["get_daily"] == 1
            assert await client.ttl(key) > 0
        finally:
            await client.delete(key)
            await client.aclose()

    asyncio.run(scenario())
