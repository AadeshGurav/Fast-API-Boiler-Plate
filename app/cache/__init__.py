"""Cache backends. Select with ``app_cache_provider``: ``redis``, ``memory`` or
``package.module:YourCache`` (a ``CacheInterface`` implementation)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.cache.interface import CacheInterface, CacheUnavailableError, RateDecision
from app.core.plugins import load_backend_class

if TYPE_CHECKING:
    from app.services.logger import Logger
    from config import Config

BUILTIN_CACHES = {
    "redis": "app.cache.redis:RedisCache",
    "memory": "app.cache.memory:MemoryCache",
}


def create_cache(config: Config, logger: Logger) -> CacheInterface:
    """Instantiate the configured cache backend."""
    cls = load_backend_class(config["app_cache_provider"], BUILTIN_CACHES, "cache")
    return cls(config, logger)


__all__ = [
    "BUILTIN_CACHES",
    "CacheInterface",
    "CacheUnavailableError",
    "RateDecision",
    "create_cache",
]
