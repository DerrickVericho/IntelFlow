"""Cache availability failures."""

from .base import AppError


class CacheUnavailable(AppError):
    """Redis cannot safely serve or persist a paid upstream response."""

    code = "CACHE_UNAVAILABLE"
    http_status = 503
