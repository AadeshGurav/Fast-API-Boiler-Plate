"""Reject oversized request bodies before they are buffered in memory."""

from __future__ import annotations

import asyncio
import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

PROBLEM_JSON = b"application/problem+json"


class BodySizeLimitMiddleware:
    """Pure-ASGI limit on request body size (413 Payload Too Large).

    FastAPI parses multipart bodies into memory before a handler runs, so without a cap
    one request can exhaust the process. The declared ``Content-Length`` is checked up
    front; bodies without one (chunked transfer) are counted as they stream in. A client
    that stops sending mid-body is cut off after ``idle_timeout`` seconds (408), so a trickling
    request cannot hold a worker slot (slowloris); waiting for the *response* is not limited.
    """

    def __init__(self, app: ASGIApp, max_body_bytes: int, idle_timeout: float = 15.0) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.idle_timeout = idle_timeout

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Enforce the limit on HTTP requests; pass everything else through."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = dict(scope["headers"]).get(b"content-length")
        if declared and declared.isdigit() and int(declared) > self.max_body_bytes:
            await self._reject(send)
            return

        received = 0
        body_done = False
        response_started = False

        async def counting_receive() -> Message:
            nonlocal received, body_done
            if body_done:  # only the disconnect signal is left: it may legitimately take long
                return await receive()
            try:
                message = await asyncio.wait_for(receive(), self.idle_timeout)
            except TimeoutError:
                raise _BodyStalled from None
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                body_done = not message.get("more_body", False)
                if received > self.max_body_bytes:
                    raise _BodyTooLarge
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            response_started = response_started or message["type"] == "http.response.start"
            await send(message)

        try:
            await self.app(scope, counting_receive, tracking_send)
        except _BodyTooLarge:
            if not response_started:
                await self._reject(send)
        except _BodyStalled:
            if not response_started:
                await self._reject(
                    send, 408, "Request Timeout", "request_timeout", "The request body stalled."
                )

    async def _reject(
        self,
        send: Send,
        status: int = 413,
        title: str = "Payload Too Large",
        code: str = "payload_too_large",
        detail: str | None = None,
    ) -> None:
        body = json.dumps(
            {
                "type": "about:blank",
                "title": title,
                "status": status,
                "detail": detail or f"Request body exceeds {self.max_body_bytes} bytes.",
                "code": code,
            }
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", PROBLEM_JSON),
                    (b"content-length", str(len(body)).encode()),
                    (b"connection", b"close"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


class _BodyStalled(Exception):
    """Raised inside the receive channel when the client stops sending the body."""


class _BodyTooLarge(Exception):
    """Raised inside the receive channel when the streamed body passes the limit."""
