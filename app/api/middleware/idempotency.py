"""Idempotency keys for unsafe requests (``Idempotency-Key`` header).

A client that retries a POST/PUT/PATCH/DELETE after a timeout must not run it twice. With the
header present, the first request runs normally and its response is stored; a retry with the
same key and the same body (for multipart or large bodies: the same size) gets the stored response replayed (``Idempotent-Replayed: true``)
instead of running again. The same key with a *different* body is rejected (422), and a retry
while the first request is still running gets 409.

Keys are scoped to the caller's credentials, method and path, so one user cannot replay or
probe another's. Server errors and auth/limit rejections are never stored (retrying them is
the point). Without the header nothing changes.
"""

from __future__ import annotations

import base64
import hashlib
import re

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import Message, Receive, Send

from app.cache import CacheUnavailableError

from .base import BaseMiddleware

KEY_PATTERN = re.compile(r"[A-Za-z0-9_-]{8,128}")
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
NOT_STORED = {401, 403, 408, 425, 429}
MAX_STORED_BODY = 1_048_576  # larger responses are not replayable; the claim is released
MAX_BUFFERED_REQUEST = 1_048_576  # larger request bodies are streamed, never held in memory
REPLAYED_HEADERS = ("content-type", "location", "content-disposition")


def _problem(status: int, title: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"type": "about:blank", "title": title, "status": status, "detail": detail},
        media_type="application/problem+json",
    )


class IdempotencyMiddleware(BaseMiddleware):
    """Replays stored responses for retried unsafe requests that carry an Idempotency-Key."""

    def initialize(self, cache, **kwargs) -> None:
        self.cache = cache
        self.ttl: int = self.config["idempotency_ttl_seconds"]

    async def handle(self, request: Request, receive: Receive, send: Send) -> None:
        """Run, replay or reject depending on what is stored under the caller's key."""
        key = request.headers.get("idempotency-key")
        if request.method not in UNSAFE_METHODS or key is None:
            await self.app(request.scope, receive, send)
            return
        if not KEY_PATTERN.fullmatch(key):
            await _problem(
                400, "Bad Request", "Idempotency-Key must be 8-128 letters, digits, '-' or '_'."
            )(request.scope, receive, send)
            return

        # Small JSON-like bodies are buffered and hashed. Multipart bodies (random boundary on
        # every retry) and large ones (uploads) are streamed straight through, with their
        # declared length standing in for the content, so idempotency never costs a file's
        # worth of memory.
        length = request.headers.get("content-length")
        streamed = (
            length is None  # chunked: its size is unknown, so never buffer it before auth
            or not length.isdigit()
            or request.headers.get("content-type", "").startswith("multipart/")
            or int(length) > MAX_BUFFERED_REQUEST
        )
        body = b""
        if streamed:
            body_hash = f"length:{length or 'unknown'}"
            app_receive = receive
        else:
            body = await self._read_body(receive)
            body_hash = hashlib.sha256(body).hexdigest()
            app_receive = None  # set below once the replaying receive exists
        credentials = request.headers.get("authorization") or request.headers.get("cookie") or ""
        scope_hash = hashlib.sha256(
            f"{credentials}|{request.method}|{request.url.path}?{request.url.query}|{key}".encode()
        ).hexdigest()
        cache_key = f"idempotency:{scope_hash}"

        try:
            claimed = await self.cache.add(
                cache_key, {"state": "running", "body": body_hash}, self.ttl
            )
        except CacheUnavailableError:
            # Running it unprotected could duplicate the effect the client asked us to guard.
            response = _problem(
                503, "Service Unavailable", "Idempotency protection is unavailable; retry shortly."
            )
            response.headers["Retry-After"] = "5"
            await response(request.scope, receive, send)
            return
        if not claimed:
            await self._answer_retry(cache_key, body_hash)(request.scope, receive, send)
            return

        async def replay_receive() -> Message:
            nonlocal body
            chunk, body = body, b""
            return {"type": "http.request", "body": chunk, "more_body": False}

        status = 500
        headers: list[tuple[bytes, bytes]] = []
        captured = bytearray()
        too_big = False

        async def capture_send(message: Message) -> None:
            nonlocal status, headers, too_big
            if message["type"] == "http.response.start":
                status, headers = message["status"], list(message.get("headers", []))
            elif message["type"] == "http.response.body":
                captured.extend(message.get("body", b""))
                too_big = too_big or len(captured) > MAX_STORED_BODY
            await send(message)

        try:
            await self.app(request.scope, app_receive or replay_receive, capture_send)
        except BaseException:
            await self.cache.delete(cache_key)
            raise

        if status >= 500 or status in NOT_STORED or too_big:
            await self.cache.delete(cache_key)  # let the client retry for real
            return
        await self.cache.set(
            cache_key,
            {
                "state": "done",
                "body": body_hash,
                "status": status,
                "headers": [
                    [k.decode(), v.decode()]
                    for k, v in headers
                    if k.decode().lower() in REPLAYED_HEADERS
                ],
                "content": base64.b64encode(bytes(captured)).decode(),
            },
            self.ttl,
        )

    @staticmethod
    async def _read_body(receive: Receive) -> bytes:
        body = bytearray()
        while True:
            message = await receive()
            body.extend(message.get("body", b""))
            if not message.get("more_body", False):
                return bytes(body)

    def _answer_retry(self, cache_key: str, body_hash: str):
        async def respond(scope, receive, send) -> None:
            stored = await self.cache.get(cache_key)
            if not stored or stored["state"] == "running":
                response: Response = _problem(
                    409, "Conflict", "A request with this Idempotency-Key is still being processed."
                )
            elif stored["body"] != body_hash:
                response = _problem(
                    422,
                    "Unprocessable Entity",
                    "This Idempotency-Key was used with a different request body.",
                )
            else:
                response = Response(
                    content=base64.b64decode(stored["content"]),
                    status_code=stored["status"],
                    headers={**dict(stored["headers"]), "Idempotent-Replayed": "true"},
                )
            await response(scope, receive, send)

        return respond


__all__ = ["IdempotencyMiddleware"]
