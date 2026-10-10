"""Distributed rate limiting middleware for FastAPI.

Supports sliding and fixed window algorithms using Redis Lua scripts.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from starlette.types import Receive, Send

from app.utils.utils import client_ip

from .base import BaseMiddleware, set_headers

if TYPE_CHECKING:
    from app.services.cache import CacheService


class RateLimiter(BaseMiddleware):
    """Distributed rate limiting middleware with sliding/fixed window algorithms.

    Requests are counted per client IP and per *tier* (login, API, ...), not per URL:
    keying on the full path would give every distinct path its own allowance, so
    walking ``/files/1``, ``/files/2``... would never be limited.

    If Redis is unreachable the limiter fails open (availability over throttling) and
    logs an error; account lockout still protects logins.
    """

    # Paths probed by orchestrators/monitoring are never throttled.
    UNTHROTTLED_KEYWORDS = (
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/ready",
        "/live",
        "/startup",
    )

    def initialize(self: RateLimiter, cache: CacheService, **kwargs) -> None:
        """Read limits from config.

        Args:
        ----
            cache: Cache service used for counting
            kwargs: Additional keyword arguments

        """
        self.cache = cache
        self.requests_limit = self.config["rate_limit_requests"]
        self.window_seconds = self.config["rate_limit_window"]
        self.prefix = self.config["rate_limit_prefix"]
        self.algorithm = self.config["rate_limit_algorithm"]
        self.rate_limit_tiers = self.config["rate_limit_tiers"]
        self.exclude_paths = [
            path
            for path in self.public_paths
            if any(keyword in path for keyword in self.UNTHROTTLED_KEYWORDS)
        ]
        self.logger.info("RateLimiter initialized", extra={"middleware": "RateLimiter"})

    def _determine_tier(self: RateLimiter, path: str) -> tuple[str, int, int]:
        """The (tier name, limit, window seconds) that applies to ``path``."""
        for name, tier in self.rate_limit_tiers.items():
            if any(pattern in path for pattern in tier.get("patterns", [])):
                return (
                    name,
                    tier.get("requests", self.requests_limit),
                    tier.get("window", self.window_seconds),
                )
        default = self.rate_limit_tiers.get("default", {})
        return (
            "default",
            default.get("requests", self.requests_limit),
            default.get("window", self.window_seconds),
        )

    async def handle(self, request: Request, receive: Receive, send: Send) -> None:
        """Count the request against its tier; answer 429 when over the limit."""
        if request.method == "OPTIONS":
            await self.app(request.scope, receive, send)
            return

        tier, limit, window = self._determine_tier(request.url.path)
        key = f"{self.prefix}{tier}:{client_ip(request)}"

        try:
            decision = await self.cache.hit(
                key, limit, window, sliding=self.algorithm == "sliding_window"
            )
            allowed, current, retry_after = (
                decision.allowed,
                decision.current,
                decision.retry_after,
            )
        except Exception as e:
            self.logger.error(
                f"Rate limit check failed, allowing request: {e}",
                extra={"middleware": "RateLimiter"},
            )
            await self.app(request.scope, receive, send)
            return

        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(max(0, limit - current)),
            "X-RateLimit-Reset": str(int(time.time()) + window),
        }
        if not allowed:
            wait = int(retry_after or window)
            self.logger.warning(
                f"Rate limit exceeded for {key}",
                extra={
                    "path": request.url.path,
                    "tier": tier,
                    "limit": limit,
                    "middleware": "RateLimiter",
                },
            )
            response = JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "type": "about:blank",
                    "title": "Too Many Requests",
                    "status": HTTP_429_TOO_MANY_REQUESTS,
                    "detail": f"Rate limit exceeded. Retry after {wait}s.",
                    "code": "rate_limited",
                },
                media_type="application/problem+json",
                headers={**headers, "Retry-After": str(wait)},
            )
            await response(request.scope, receive, send)
            return

        await self.forward(
            request, receive, send, on_start=lambda message: set_headers(message, headers)
        )
