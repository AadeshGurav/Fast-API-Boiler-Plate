"""Redis cache backend."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

import redis.asyncio as redis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialWithJitterBackoff

from app.cache.interface import CacheInterface, RateDecision

SLIDING_WINDOW_SCRIPT = """
local key, now, window, limit, member = KEYS[1], tonumber(ARGV[1]), tonumber(ARGV[2]), tonumber(ARGV[3]), ARGV[4]
redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
local current = redis.call('ZCARD', key)
if current < limit then
    redis.call('ZADD', key, now, member)
    redis.call('EXPIRE', key, window)
    return {1, current + 1, 0}
end
local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
local retry = window
if oldest[2] then retry = math.ceil(oldest[2] + window - now) end
return {0, current, retry}
"""

FIXED_WINDOW_SCRIPT = """
local key, limit, window = KEYS[1], tonumber(ARGV[1]), tonumber(ARGV[2])
local current = redis.call('INCR', key)
if current == 1 then redis.call('EXPIRE', key, window) end
if current <= limit then return {1, current, 0} end
return {0, current, redis.call('TTL', key)}
"""


class RedisCache(CacheInterface):
    """Redis-backed cache (settings: ``redis_host/port/password/max_connections``)."""

    def __init__(self, config, logger) -> None:
        super().__init__(config, logger)
        self.client: redis.Redis | None = None

    async def connect(self) -> None:
        self.client = redis.Redis(
            host=self.config["redis_host"],
            port=self.config["redis_port"],
            password=self.config["redis_password"] or None,
            decode_responses=True,
            max_connections=self.config["redis_max_connections"],
            socket_connect_timeout=self.config["cache_timeout_seconds"],
            socket_timeout=self.config["cache_timeout_seconds"],
            health_check_interval=30,
            # One quick retry rides out a dropped connection; redis-py's default (three
            # retries backing off from 1 s) would hold the first request of an outage for
            # ~4 s before CacheService's circuit can open.
            retry=Retry(ExponentialWithJitterBackoff(base=0.05, cap=0.25), retries=1),
        )
        try:
            await self.client.ping()
        except Exception:
            await self.client.aclose()
            self.client = None
            raise
        self.logger.info("Connected to Redis")

    async def close(self) -> None:
        if self.client:
            await self.client.aclose()
            self.client = None

    async def health_check(self) -> bool:
        try:
            return bool(self.client and await self.client.ping())
        except Exception as e:
            self.logger.error(f"Redis health check failed: {e}")
            return False

    @property
    def is_connected(self) -> bool:
        return self.client is not None

    def _require(self) -> redis.Redis:
        if self.client is None:
            raise RuntimeError("Redis is not connected")
        return self.client

    async def get(self, key: str) -> Any:
        raw = await self._require().get(key)
        return None if raw is None else json.loads(raw)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        return bool(await self._require().set(key, json.dumps(value, default=str), ex=ttl or None))

    async def add(self, key: str, value: Any, ttl: int | None = None) -> bool:
        return bool(
            await self._require().set(key, json.dumps(value, default=str), ex=ttl or None, nx=True)
        )

    async def delete(self, *keys: str) -> int:
        return await self._require().delete(*keys) if keys else 0

    async def delete_prefix(self, prefix: str) -> int:
        client = self._require()
        deleted = 0
        # SCAN in batches rather than KEYS (which blocks the server); UNLINK frees lazily.
        batch: list[str] = []
        async for key in client.scan_iter(match=f"{prefix}*", count=500):
            batch.append(key)
            if len(batch) >= 500:
                deleted += await client.unlink(*batch)
                batch = []
        if batch:
            deleted += await client.unlink(*batch)
        return deleted

    async def hit(self, key: str, limit: int, window: int, *, sliding: bool = True) -> RateDecision:
        client = self._require()
        if sliding:
            result = await client.eval(
                SLIDING_WINDOW_SCRIPT, 1, key, time.time(), window, limit, uuid.uuid4().hex
            )
        else:
            result = await client.eval(FIXED_WINDOW_SCRIPT, 1, key, limit, window)
        allowed, current, retry = bool(result[0]), int(result[1]), int(result[2])
        return RateDecision(allowed, current, None if allowed else max(1, retry))
