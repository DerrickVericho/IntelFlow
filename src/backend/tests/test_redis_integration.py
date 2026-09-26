"""Opt-in test against a real Redis; creates and deletes only one unique key."""

import asyncio
import json
import os
from dataclasses import replace
from uuid import uuid4

import pytest
from redis.asyncio import Redis

from src.backend.cache.store import RedisCache
from src.backend.sectors.cached import CachedSectorsGateway
from src.backend.sectors.utils import canonical_key
from src.backend.tests.conftest import make_settings
from src.backend.tests.fixtures import FixtureTransport, TODAY


@pytest.mark.redis_integration
@pytest.mark.skipif(not os.getenv("TEST_REDIS_URL"), reason="Set TEST_REDIS_URL for real Redis")
def test_real_redis_cache_survives_gateway_recreation() -> None:
    async def scenario() -> None:
        redis = Redis.from_url(os.environ["TEST_REDIS_URL"], decode_responses=True)
        prefix = "intelflow:test:" + uuid4().hex
        settings = replace(make_settings(), redis_key_prefix=prefix)
        params = {"start": "2026-09-01", "end": TODAY.isoformat()}
        key = canonical_key(prefix, "get_daily", "TEST", params)
        transport = FixtureTransport()
        transport.rows[0]["future_field"] = "retained"
        try:
            await redis.ping()
            first = CachedSectorsGateway(transport, RedisCache(redis), settings, utc_today=lambda: TODAY)
            initial = await first.get_daily("TEST", **params)
            second = CachedSectorsGateway(transport, RedisCache(redis), settings, utc_today=lambda: TODAY)
            restored = await second.get_daily("test.jk", **params)
            assert restored.data == initial.data
            assert transport.calls["get_daily"] == 1
            assert await redis.ttl(key) > 0
            cached = json.loads(await redis.get(key))
            assert cached["payload"][0]["future_field"] == "retained"
        finally:
            await redis.delete(key)
            await redis.aclose()

    asyncio.run(scenario())
