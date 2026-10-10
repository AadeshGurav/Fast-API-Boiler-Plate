"""Cross-site request forgery defence for cookie-authenticated requests.

Cookies ride along on requests a hostile page triggers, so state-changing requests that
authenticate by cookie must come from an origin we trust. ``SameSite=Lax`` already stops the
common cases; this closes the gaps (``SameSite=None`` deployments, sibling subdomains, old
browsers) with the standard Origin/Referer check. Requests that carry an ``Authorization``
header, or no cookies at all, are not forgeable this way and pass untouched, as do requests
without an Origin or Referer (not sent by browsers on cross-site writes).
"""

from __future__ import annotations

import json
from urllib.parse import urlsplit

from starlette.types import ASGIApp, Receive, Scope, Send

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class CSRFOriginMiddleware:
    """Pure-ASGI Origin check (403) for unsafe, cookie-authenticated requests."""

    def __init__(self, app: ASGIApp, allowed_origins: list[str]) -> None:
        self.app = app
        self.allowed = {origin.rstrip("/").lower() for origin in allowed_origins}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in SAFE_METHODS:
            await self.app(scope, receive, send)
            return
        headers = {k.lower(): v for k, v in scope["headers"]}
        if b"authorization" in headers or b"cookie" not in headers:
            await self.app(scope, receive, send)
            return

        source = headers.get(b"origin") or headers.get(b"referer")
        if source and not self._trusted(source.decode("latin-1"), headers.get(b"host", b"")):
            await self._reject(send)
            return
        await self.app(scope, receive, send)

    def _trusted(self, source: str, host: bytes) -> bool:
        parts = urlsplit(source)
        if not parts.scheme or not parts.netloc:  # "null" and other opaque origins
            return False
        origin = f"{parts.scheme}://{parts.netloc}".lower()
        return origin in self.allowed or parts.netloc.lower() == host.decode("latin-1").lower()

    @staticmethod
    async def _reject(send: Send) -> None:
        body = json.dumps(
            {
                "type": "about:blank",
                "title": "Forbidden",
                "status": 403,
                "detail": "Cross-site request refused: its Origin is not allowed.",
                "code": "csrf_origin_rejected",
            }
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 403,
                "headers": [
                    (b"content-type", b"application/problem+json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
