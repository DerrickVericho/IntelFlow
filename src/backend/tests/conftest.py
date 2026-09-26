"""Shared, repository-owned inputs for the offline backend contract tests."""

from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from src.backend.cache.store import MemoryCache
from src.backend.config import Settings
from src.backend.main import create_app
from src.backend.sectors.cached import CachedSectorsGateway
from src.backend.services.research import ResearchService
from src.backend.tests.fixtures import FixtureTransport, TODAY


def make_settings() -> Settings:
    """Use fixed settings so tests never depend on a developer's .env file."""
    return Settings(
        redis_url="redis://localhost:6379/0",
        redis_key_prefix="intelflow:test",
        redis_connect_timeout_seconds=1.0,
        redis_socket_timeout_seconds=1.0,
        redis_health_check_interval_seconds=0,
        cache_ttl_market_current_seconds=60,
        cache_ttl_market_historical_seconds=3600,
        cache_ttl_shareholders_seconds=60,
        cache_ttl_free_float_seconds=60,
        cache_ttl_company_dynamic_seconds=60,
        cache_ttl_company_static_seconds=3600,
        cache_ttl_revenue_segments_seconds=3600,
    )


@dataclass
class Harness:
    transport: FixtureTransport
    cache: MemoryCache
    gateway: CachedSectorsGateway
    service: ResearchService


@pytest.fixture
def harness() -> Harness:
    transport = FixtureTransport()
    cache = MemoryCache()
    gateway = CachedSectorsGateway(
        transport, cache, make_settings(), utc_today=lambda: TODAY
    )
    service = ResearchService(gateway, today=lambda: TODAY, utc_today=lambda: TODAY)
    return Harness(transport, cache, gateway, service)


@pytest.fixture
def client(harness: Harness) -> Iterator[TestClient]:
    with TestClient(create_app(service=harness.service)) as test_client:
        yield test_client
