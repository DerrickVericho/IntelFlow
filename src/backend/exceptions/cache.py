"""Cache availability failures."""


class CacheUnavailable(RuntimeError):
    """Redis cannot safely serve or persist a paid upstream response."""
