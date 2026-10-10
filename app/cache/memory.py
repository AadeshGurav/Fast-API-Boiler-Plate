"""In-process cache: for tests, single-process deployments and as a reference backend.

Not shared between worker processes: with several workers, rate limits and cached data
differ per worker. Use a networked backend (Redis) in that case.
"""

from __future__ import annotations

import json
import time
from collections import deque
from typing import Any

from app.cache.interface import CacheInterface, RateDecision


class MemoryCache(CacheInterface):
    """Dict-backed cache with lazy expiry."""

    def __init__(self, config, logger) -> None:
        super().__init__(config, logger)
        self._items: dict[str, tuple[str, float | None]] = {}
        self._windows: dict[str, deque[float]] = {}
        self._fixed: dict[str, tuple[int, float]] = {}
        self._connected = False

    async def connect(self) -> None:
        self._connected = True

    async def close(self) -> None:
        self._connected = False

    async def health_check(self) -> bool:
        return self._connected

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def get(self, key: str) -> Any:
        entry = self._items.get(key)
        if entry is None:
            return None
        raw, expires = entry
        if expires is not None and expires <= time.monotonic():
            del self._items[key]
            return None
        return json.loads(raw)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        self._items[key] = (
            json.dumps(value, default=str),
            time.monotonic() + ttl if ttl else None,
        )
        return True

    async def add(self, key: str, value: Any, ttl: int | None = None) -> bool:
        if await self.get(key) is not None:
            return False
        return await self.set(key, value, ttl)

    async def delete(self, *keys: str) -> int:
        return sum(self._items.pop(key, None) is not None for key in keys)

    async def delete_prefix(self, prefix: str) -> int:
        return await self.delete(*[k for k in self._items if k.startswith(prefix)])

    async def hit(self, key: str, limit: int, window: int, *, sliding: bool = True) -> RateDecision:
        now = time.monotonic()
        if sliding:
            hits = self._windows.setdefault(key, deque())
            while hits and hits[0] <= now - window:
                hits.popleft()
            if len(hits) >= limit:
                return RateDecision(False, len(hits), max(1, int(hits[0] + window - now) + 1))
            hits.append(now)
            return RateDecision(True, len(hits), None)

        count, reset = self._fixed.get(key, (0, now + window))
        if reset <= now:
            count, reset = 0, now + window
        count += 1
        self._fixed[key] = (count, reset)
        allowed = count <= limit
        return RateDecision(allowed, count, None if allowed else max(1, int(reset - now) + 1))
