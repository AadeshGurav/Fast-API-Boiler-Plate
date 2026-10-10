"""Namespaced access to the configured cache backend, with graceful degradation.

The cache is an accelerator, not a source of truth, so losing it must slow the app down
rather than take it down:

* reads behave as misses (the database answers) and writes are skipped;
* after a failure the backend is left alone for ``cache_failure_cooldown_seconds`` instead of
  making every request wait out a timeout (the circuit is *open*);
* a failed delete is logged loudly and left to expire by TTL, because failing a request whose
  database write already succeeded would be worse;
* operations that are meaningless without the cache (rate counting, idempotency claims) raise
  ``CacheUnavailableError`` immediately so their callers can choose: the rate limiter fails
  open, idempotent requests get a 503.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from app.cache import CacheInterface, CacheUnavailableError, RateDecision, create_cache
from app.services.base_service import BaseService

if TYPE_CHECKING:
    from app.services.logger import Logger
    from config import Config


class CacheService(BaseService):
    """Prefixes keys, applies the default TTL and delegates to a ``CacheInterface``."""

    def __init__(self, config: Config, logger: Logger) -> None:
        super().__init__(config, logger)
        self.default_ttl: int = config["cache_default_ttl"]
        self.prefix: str = config["cache_prefix"]
        self.cooldown: int = config["cache_failure_cooldown_seconds"]
        self.backend: CacheInterface = create_cache(config, logger)
        self._skip_until = 0.0  # monotonic time before which the backend is not contacted
        self.logger.info("CacheService initialized", extra={"service": "CacheService"})

    # ---- circuit ------------------------------------------------------------------------
    @property
    def available(self) -> bool:
        """False while the cool-down after a backend failure is running."""
        return time.monotonic() >= self._skip_until

    def _record_failure(self, operation: str, error: Exception) -> None:
        self._skip_until = time.monotonic() + self.cooldown
        self.logger.error(
            f"Cache {operation} failed ({error!r}); not using the cache for {self.cooldown}s",
            extra={"service": "CacheService", "operation": operation},
        )

    def _require_available(self) -> None:
        if not self.available:
            raise CacheUnavailableError("cache is cooling down after a failure")

    # ---- degradable operations ------------------------------------------------------------
    async def get(self, key: str) -> Any:
        """The cached value, or None (also when the cache is down)."""
        if not self.available:
            return None
        try:
            return await self.backend.get(f"{self.prefix}{key}")
        except Exception as e:
            self._record_failure("get", e)
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Cache ``value`` for ``ttl`` seconds (default ``cache_default_ttl``); False if skipped."""
        if not self.available:
            return False
        try:
            return await self.backend.set(f"{self.prefix}{key}", value, ttl or self.default_ttl)
        except Exception as e:
            self._record_failure("set", e)
            return False

    async def delete(self, key: str) -> int:
        """Drop one key. If the cache is down the entry is left to expire by TTL."""
        if not self.available:
            return 0
        try:
            return await self.backend.delete(f"{self.prefix}{key}")
        except Exception as e:
            self._record_failure("delete", e)
            return 0

    async def clear_pattern(self, pattern: str) -> int:
        """Drop every key whose name starts with ``pattern`` (a trailing ``*`` is allowed)."""
        if not self.available:
            return 0
        try:
            return await self.backend.delete_prefix(f"{self.prefix}{pattern.rstrip('*')}")
        except Exception as e:
            self._record_failure("clear_pattern", e)
            return 0

    # ---- operations with no fallback ----------------------------------------------------------
    async def add(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Cache ``value`` only if the key is absent; True if this call stored it.

        Raises:
        ------
            CacheUnavailableError: The cache is down (the claim cannot be made).

        """
        self._require_available()
        try:
            return await self.backend.add(f"{self.prefix}{key}", value, ttl or self.default_ttl)
        except Exception as e:
            self._record_failure("add", e)
            raise CacheUnavailableError(str(e)) from e

    async def hit(self, key: str, limit: int, window: int, *, sliding: bool = True) -> RateDecision:
        """Count a request against a rate limit (not prefixed with the cache namespace).

        Raises:
        ------
            CacheUnavailableError: The cache is down (the limiter fails open).

        """
        self._require_available()
        try:
            return await self.backend.hit(key, limit, window, sliding=sliding)
        except Exception as e:
            self._record_failure("hit", e)
            raise CacheUnavailableError(str(e)) from e

    # ---- lifecycle ----------------------------------------------------------------------------
    async def connect(self) -> None:
        """Connect the backend."""
        await self.backend.connect()

    async def close(self) -> None:
        """Close the backend."""
        await self.backend.close()

    async def health_check(self) -> bool:
        """Whether the backend answers (asked directly, so recovery is noticed promptly)."""
        return await self.backend.health_check()

    @property
    def is_connected(self) -> bool:
        """Whether the backend is connected."""
        return self.backend.is_connected
