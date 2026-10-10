"""One log line and one metrics sample per request, plus the ``X-Process-Time`` header."""

from __future__ import annotations

import time

from starlette.requests import Request
from starlette.types import Message, Receive, Send

from .base import BaseMiddleware, set_headers


class AccessLogMiddleware(BaseMiddleware):
    """Logs ``METHOD /path -> status (ms)`` and records Prometheus metrics when enabled."""

    def initialize(self, metrics=None, **kwargs) -> None:
        self.metrics = metrics

    async def handle(self, request: Request, receive: Receive, send: Send) -> None:
        """Time the request and report it once it has been answered."""
        started = time.perf_counter()
        elapsed = 0.0

        def add_timing(message: Message) -> None:
            nonlocal elapsed
            elapsed = time.perf_counter() - started
            set_headers(message, {"X-Process-Time": f"{elapsed:.4f}"})

        status = None
        try:
            status = await self.forward(request, receive, send, on_start=add_timing)
        finally:
            elapsed = elapsed or time.perf_counter() - started
            code = status or 500
            self.logger.info(
                f"{request.method} {request.url.path} -> {code}",
                extra={
                    "status": code,
                    "duration_ms": round(elapsed * 1000, 1),
                    "client": request.client.host if request.client else None,
                    "user_id": getattr(request.state, "user_id", None),
                },
            )
            if self.metrics is not None:
                # The matched route *template* ("/files/{file_id}"); raw URLs would give every
                # scanned path its own time series.
                route = request.scope.get("route")
                self.metrics.track_request(
                    request.method, getattr(route, "path", None) or "unmatched", code, elapsed
                )
