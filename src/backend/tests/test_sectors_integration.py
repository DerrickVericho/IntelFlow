"""One-credit opt-in contract check against the real Sectors daily endpoint."""

import asyncio
import json
import os
from dataclasses import replace
from datetime import date
from unittest.mock import Mock
from uuid import uuid4

import pytest
from redis.asyncio import Redis

from src.backend.cache.store import MemoryCache, RedisCache
from src.backend.sectors.cached import CachedSectorsGateway
from src.backend.sectors.client import SectorsClient
from src.backend.sectors.utils import canonical_key
from src.backend.tests.conftest import make_settings


@pytest.mark.live_sectors
@pytest.mark.skipif(os.getenv("RUN_SECTORS_TESTS") != "1", reason="Set RUN_SECTORS_TESTS=1 for paid Sectors integration")
def test_live_daily_response_matches_gateway_contract() -> None:
    if not os.getenv("SECTORS_API_KEY"):
        pytest.fail("SECTORS_API_KEY must be set in the process environment")

    async def scenario() -> None:
        redis_url = os.getenv("TEST_REDIS_URL")
        redis = Redis.from_url(redis_url, decode_responses=True) if redis_url else None
        prefix = "intelflow:live-test:" + uuid4().hex
        settings = replace(make_settings(), redis_key_prefix=prefix)
        cache = RedisCache(redis) if redis else MemoryCache()
        params = {"start": "2025-05-01", "end": "2025-05-14"}
        key = canonical_key(prefix, "get_daily", "BBCA", params)
        with SectorsClient(timeout=(5.0, 15.0)) as transport:
            try:
                if redis:
                    await redis.ping()
                gateway = CachedSectorsGateway(transport, cache, settings)
                result = await gateway.get_daily("BBCA", **params)
                assert result.data, "Expected historical BBCA observations"
                assert all(row.symbol == "BBCA.JK" for row in result.data)
                assert all(date(2025, 5, 1) <= row.date <= date(2025, 5, 14) for row in result.data)
                assert all(row.close > 0 and row.volume >= 0 for row in result.data)
                if redis:
                    cached = json.loads(await redis.get(key))
                    assert cached["payload"]
                    assert await redis.ttl(key) > 0
                    offline = Mock()
                    offline.get_daily.side_effect = AssertionError("Cache miss after live fetch")
                    restored = await CachedSectorsGateway(offline, RedisCache(redis), settings).get_daily("BBCA", **params)
                    assert restored.data == result.data
                    offline.get_daily.assert_not_called()
                else:
                    assert cache.values, "Validated provider JSON should be cached"
            finally:
                if redis:
                    await redis.delete(key)
                    await redis.aclose()

    asyncio.run(scenario())
