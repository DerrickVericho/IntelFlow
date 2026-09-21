"""Environment-backed configuration for the IntelFlow backend."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlparse

from dotenv import load_dotenv


class ApplicationConfigurationError(RuntimeError):
    """Raised when backend environment configuration is invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated application settings loaded from environment variables."""

    redis_url: str
    redis_key_prefix: str
    redis_connect_timeout_seconds: float
    redis_socket_timeout_seconds: float
    redis_health_check_interval_seconds: int
    cache_ttl_market_current_seconds: int
    cache_ttl_market_historical_seconds: int
    cache_ttl_shareholders_seconds: int
    cache_ttl_free_float_seconds: int
    cache_ttl_company_dynamic_seconds: int
    cache_ttl_company_static_seconds: int
    cache_ttl_revenue_segments_seconds: int

    @classmethod
    def from_env(cls) -> Settings:
        """Build settings from the process environment and local `.env`."""

        load_dotenv()

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0").strip()
        parsed_url = urlparse(redis_url)
        if parsed_url.scheme not in {"redis", "rediss", "unix"}:
            raise ApplicationConfigurationError(
                "REDIS_URL must use redis://, rediss://, or unix://."
            )

        redis_key_prefix = os.getenv(
            "REDIS_KEY_PREFIX", "intelflow:sectors:v1"
        ).strip()
        if not redis_key_prefix or any(char.isspace() for char in redis_key_prefix):
            raise ApplicationConfigurationError(
                "REDIS_KEY_PREFIX must be non-empty and contain no whitespace."
            )

        return cls(
            redis_url=redis_url,
            redis_key_prefix=redis_key_prefix,
            redis_connect_timeout_seconds=_positive_float(
                "REDIS_CONNECT_TIMEOUT_SECONDS", 2.0
            ),
            redis_socket_timeout_seconds=_positive_float(
                "REDIS_SOCKET_TIMEOUT_SECONDS", 2.0
            ),
            redis_health_check_interval_seconds=_non_negative_int(
                "REDIS_HEALTH_CHECK_INTERVAL_SECONDS", 30
            ),
            cache_ttl_market_current_seconds=_positive_int(
                "CACHE_TTL_MARKET_CURRENT_SECONDS", 3_600
            ),
            cache_ttl_market_historical_seconds=_positive_int(
                "CACHE_TTL_MARKET_HISTORICAL_SECONDS", 2_592_000
            ),
            cache_ttl_shareholders_seconds=_positive_int(
                "CACHE_TTL_SHAREHOLDERS_SECONDS", 259_200
            ),
            cache_ttl_free_float_seconds=_positive_int(
                "CACHE_TTL_FREE_FLOAT_SECONDS", 604_800
            ),
            cache_ttl_company_dynamic_seconds=_positive_int(
                "CACHE_TTL_COMPANY_DYNAMIC_SECONDS", 43_200
            ),
            cache_ttl_company_static_seconds=_positive_int(
                "CACHE_TTL_COMPANY_STATIC_SECONDS", 604_800
            ),
            cache_ttl_revenue_segments_seconds=_positive_int(
                "CACHE_TTL_REVENUE_SEGMENTS_SECONDS", 604_800
            ),
        )


def _positive_int(name: str, default: int) -> int:
    value = _integer(name, default)
    if value <= 0:
        raise ApplicationConfigurationError(f"{name} must be greater than zero.")
    return value


def _non_negative_int(name: str, default: int) -> int:
    value = _integer(name, default)
    if value < 0:
        raise ApplicationConfigurationError(f"{name} cannot be negative.")
    return value


def _integer(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ApplicationConfigurationError(f"{name} must be an integer.") from exc


def _positive_float(name: str, default: float) -> float:
    raw_value = os.getenv(name, str(default))
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ApplicationConfigurationError(f"{name} must be a number.") from exc
    if value <= 0:
        raise ApplicationConfigurationError(f"{name} must be greater than zero.")
    return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide immutable settings instance."""

    return Settings.from_env()

