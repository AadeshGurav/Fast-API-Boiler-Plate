"""Distributed rate limiting middleware for FastAPI.

Supports sliding and fixed window algorithms using Redis Lua scripts.
"""
from __future__ import annotations

import hashlib
import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from app.database.redis import Redis

from .base import BaseMiddleware

# Lua scripts for Redis atomic operations
SLIDING_WINDOW_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
local current = redis.call('ZCARD', key)
if current < limit then
    redis.call('ZADD', key, now, now)
    redis.call('EXPIRE', key, window)
    return {1, current + 1, limit}
else
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry_after = window
    if oldest[2] then retry_after = math.ceil(oldest[2] + window - now) end
    return {0, current, limit, retry_after}
end
"""

FIXED_WINDOW_SCRIPT = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local current = redis.call('INCR', key)
if current == 1 then redis.call('EXPIRE', key, window) end
if current <= limit then
    return {1, current, limit, redis.call('TTL', key)}
else
    return {0, current, limit, redis.call('TTL', key)}
end
"""


class RateLimiter(BaseMiddleware):
    """Distributed rate limiting middleware with sliding/fixed window algorithms."""

    def initialize(
        self: RateLimiter,
        redis_client: Redis | None = None,
        **kwargs,
    ) -> None:
        """Initialize RateLimiter middleware configuration.

        Args:
        ----
            redis_client: Redis client instance
            kwargs: Additional keyword arguments

        """
        self.redis_client = redis_client or getattr(self.app.state, "redis", None)
        self.requests_limit = self.config.get("rate_limit_requests", 100)
        self.window_seconds = self.config.get("rate_limit_window", 60)
        self.prefix = self.config.get("rate_limit_prefix", "rate_limit:")
        self.algorithm = self.config.get("rate_limit_algorithm", "sliding_window")
        self.rate_limit_tiers = self.config.get("rate_limit_tiers", {})

        self._sliding_window_sha: str | None = None
        self._fixed_window_sha: str | None = None

        self._register_scripts()
        self._set_excluded_paths()
        self.logger.info("RateLimiter initialized", extra={"middleware": "RateLimiter"})

    def _register_scripts(self: RateLimiter) -> None:
        """Prepare Lua scripts; SHA loaded lazily on first use."""
        self._sliding_window_sha = None
        self._fixed_window_sha = None

    def _set_excluded_paths(self: RateLimiter) -> None:
        """Set default excluded/public paths for rate limiting."""
        if not self.exclude_paths:
            self.exclude_paths = [
                path
                for path in self.public_paths
                if any(
                    doc in path
                    for doc in ("/docs", "/redoc", "/openapi.json", "/health", "/ready")
                )
            ]

    def _hash_path(self: RateLimiter, path: str) -> str:
        """Generate a short hash for long paths to reduce Redis key length.

        Args:
        ----
            path: Endpoint path

        Returns:
        -------
            Hashed path string for long paths

        """
        if len(path) <= 50:
            return path
        path_hash = hashlib.md5(path.encode()).hexdigest()[:8]
        return f"{path[:20]}...{path_hash}"

    def _get_client_key(self: RateLimiter, request: Request) -> str:
        """Generate Redis key based on client IP and path.

        Args:
        ----
            request: HTTP request

        Returns:
        -------
            Redis key string for client IP and path

        """
        client_ip = request.client.host if request.client else "unknown"
        path = self._hash_path(request.url.path)
        return f"{self.prefix}{client_ip}:{path}"

    def _get_user_key(self: RateLimiter, request: Request, user_id: str) -> str:
        """Generate Redis key for authenticated user.

        Args:
        ----
            request: HTTP request
            user_id: Authenticated user ID

        Returns:
        -------
            Redis key string for authenticated user

        """
        return f"{self.prefix}user:{user_id}:{request.url.path}"

    def _determine_limits(self: RateLimiter, request: Request) -> tuple[int, int]:
        """Determine requests limit and window for a specific path or tier.

        Args:
        ----
            request: HTTP request

        Returns:
        -------
            Tuple of (limit, window) in seconds

        """
        path = request.url.path

        # First check custom tiers with patterns
        for tier_config in self.rate_limit_tiers.values():
            patterns = tier_config.get("patterns", [])
            if any(pat in path for pat in patterns):
                return tier_config.get(
                    "requests", self.requests_limit
                ), tier_config.get("window", self.window_seconds)

        # Default path-based tiers
        if path.startswith("/auth"):
            tier = self.rate_limit_tiers.get("auth", {})
        elif path.startswith("/api"):
            tier = self.rate_limit_tiers.get("api", {})
        elif path.startswith("/admin"):
            tier = self.rate_limit_tiers.get("admin", {})
        else:
            tier = self.rate_limit_tiers.get("default", {})

        return tier.get("requests", self.requests_limit), tier.get(
            "window", self.window_seconds
        )

    async def _check_sliding_window(
        self: RateLimiter, key: str, limit: int, window: int
    ) -> tuple[bool, int, int, int | None]:
        """Sliding window algorithm using Redis Lua script.

        Args:
        ----
            key: Redis key
            limit: Requests limit
            window: Window size in seconds

        Returns:
        -------
            Tuple of (allowed, current requests, limit, retry after)

        """
        if not self.redis_client or not hasattr(self.redis_client, "client"):
            self.logger.warning(
                "Rate limiting disabled: No Redis client",
                extra={"middleware": "RateLimiter"},
            )
            return True, 0, limit, None

        if not self._sliding_window_sha:
            self._sliding_window_sha = await self.redis_client.client.script_load(
                SLIDING_WINDOW_SCRIPT
            )

        try:
            result = await self.redis_client.client.evalsha(
                self._sliding_window_sha, 1, key, time.time(), window, limit
            )
            allowed = bool(result[0])
            current_requests = result[1]
            retry_after = result[3] if len(result) > 3 else None
            return allowed, current_requests, limit, retry_after
        except Exception as e:  # noqa: BLE001
            self.logger.error(
                f"Sliding window check failed: {e}", extra={"middleware": "RateLimiter"}
            )
            return True, 0, limit, None

    async def _check_fixed_window(
        self: RateLimiter, key: str, limit: int, window: int
    ) -> tuple[bool, int, int, int]:
        """Fixed window algorithm using Redis Lua script.

        Args:
        ----
            key: Redis key
            limit: Requests limit
            window: Window size in seconds

        Returns:
        -------
            Tuple of (allowed, current requests, limit, TTL)

        """
        if not self._fixed_window_sha:
            self._fixed_window_sha = await self.redis_client.client.script_load(
                FIXED_WINDOW_SCRIPT
            )

        try:
            result = await self.redis_client.client.evalsha(
                self._fixed_window_sha, 1, key, limit, window
            )
            allowed = bool(result[0])
            current_requests = result[1]
            ttl = result[3]
            return allowed, current_requests, limit, ttl
        except Exception as e:  # noqa: BLE001
            self.logger.error(
                f"Fixed window check failed: {e}", extra={"middleware": "RateLimiter"}
            )
            return True, 0, limit, window

    async def process_request(
        self: RateLimiter, request: Request, call_next: Callable
    ) -> Response:
        """Apply rate limiting to incoming requests.

        Args:
        ----
            request: HTTP request
            call_next: Next middleware or route handler

        Returns:
        -------
            HTTP response

        """
        user_id = getattr(request.state, "user_id", None)
        limit, window = self._determine_limits(request)
        key = (
            self._get_user_key(request, user_id)
            if user_id
            else self._get_client_key(request)
        )

        if self.algorithm == "sliding_window":
            allowed, current, limit, retry_after = await self._check_sliding_window(
                key, limit, window
            )
        else:
            allowed, current, limit, retry_after = await self._check_fixed_window(
                key, limit, window
            )

        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(max(0, limit - current)),
            "X-RateLimit-Reset": str(int(time.time()) + window),
        }

        if not allowed:
            self.logger.warning(
                f"Rate limit exceeded for {key}",
                extra={
                    "client_ip": request.client.host if request.client else "unknown",
                    "path": request.url.path,
                    "current_requests": current,
                    "limit": limit,
                    "user_id": user_id,
                    "middleware": "RateLimiter",
                },
            )
            headers["Retry-After"] = str(retry_after or window)
            return Response(
                content=f"Rate limit exceeded. Retry after {retry_after or window}s.",
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                headers=headers,
            )

        response = await call_next(request)
        for h, v in headers.items():
            response.headers[h] = v
        return response
