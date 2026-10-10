"""Request timeout and concurrency limiting."""

from __future__ import annotations

import asyncio

from fastapi import HTTPException
from starlette.requests import Request
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE, HTTP_504_GATEWAY_TIMEOUT
from starlette.types import Message, Receive, Send

from app.api.middleware.base import BaseMiddleware


class TimeoutMiddleware(BaseMiddleware):
    """Bounds how long a request may run and how many run at once.

    * ``request_timeout_seconds`` applies to every request unless a path prefix in
      ``endpoint_timeouts`` overrides it (e.g. file uploads).
    * ``max_concurrent_requests`` caps in-flight requests; further requests wait up to
      ``queue_wait_seconds`` seconds for a slot and are then rejected with 503, so
      overload sheds load instead of collapsing the whole service (backpressure).
    """

    def initialize(self: TimeoutMiddleware, **kwargs) -> None:
        """Read limits from config."""
        self.default_timeout: float = float(self.config["request_timeout_seconds"])
        self.endpoint_timeouts: dict[str, float] = self.config["endpoint_timeouts"]
        self.queue_wait: float = float(self.config["queue_wait_seconds"])
        max_concurrent = self.config["max_concurrent_requests"]
        self._slots = asyncio.Semaphore(max_concurrent)
        self.max_concurrent: int = max_concurrent
        self.timeout_count = 0
        self.rejected_count = 0

        self.logger.info(
            "TimeoutMiddleware initialized",
            extra={
                "middleware": "TimeoutMiddleware",
                "default_timeout": self.default_timeout,
                "max_concurrent": max_concurrent,
            },
        )

    def _get_timeout(self: TimeoutMiddleware, path: str) -> float:
        """Timeout for ``path``: the longest matching ``endpoint_timeouts`` prefix."""
        matches = [p for p in self.endpoint_timeouts if path.startswith(p)]
        if matches:
            return float(self.endpoint_timeouts[max(matches, key=len)])
        return self.default_timeout

    async def handle(self, request: Request, receive: Receive, send: Send) -> None:
        """Wait for a slot, then run the request under its timeout."""
        timeout = self._get_timeout(request.url.path)
        request.state.timeout = timeout

        try:
            await asyncio.wait_for(self._slots.acquire(), timeout=self.queue_wait)
        except TimeoutError:
            self.rejected_count += 1
            self.logger.warning(
                f"Server overloaded, rejecting {request.method} {request.url.path}",
                extra={"middleware": "TimeoutMiddleware", "max": self.max_concurrent},
            )
            raise HTTPException(
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
                detail="Server overloaded, please try again later",
                headers={"Retry-After": str(int(self.queue_wait))},
            ) from None

        response_started = False

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            response_started = response_started or message["type"] == "http.response.start"
            await send(message)

        try:
            await asyncio.wait_for(self.app(request.scope, receive, tracking_send), timeout=timeout)
        except TimeoutError:
            self.timeout_count += 1
            self.logger.warning(
                f"Request timeout: {request.method} {request.url.path}",
                extra={"middleware": "TimeoutMiddleware", "timeout_seconds": timeout},
            )
            if response_started:
                return  # the status line is already out; the connection just ends
            raise HTTPException(
                status_code=HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Request timed out after {timeout:g} seconds",
            ) from None
        finally:
            self._slots.release()
