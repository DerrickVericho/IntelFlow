"""Caching infrastructure for IntelFlow."""

from .redis_client import create_redis_client

__all__ = ["create_redis_client"]
