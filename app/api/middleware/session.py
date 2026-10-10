"""Writes silently refreshed tokens back to the browser as cookies.

Authentication happens in ``RBACMiddleware`` (inside this one). When it traded an expired
access token for a new pair using the refresh cookie, it parked the pair on
``request.state``; this middleware, wrapping it, adds the cookies when the response starts.
Session state lives in the ``sessions`` collection, referenced by the tokens' ``sid``.
"""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import Message, Receive, Send

from app.utils.cookie_manager import CookieManager

from .base import BaseMiddleware


class SessionMiddleware(BaseMiddleware):
    """Attach refreshed auth cookies to the outgoing response."""

    async def handle(self, request: Request, receive: Receive, send: Send) -> None:
        """Run the request; if tokens were refreshed, add their cookies."""

        def add_cookies(message: Message) -> None:
            new_tokens = getattr(request.state, "new_tokens", None)
            if new_tokens is None:
                return
            carrier = Response()
            CookieManager.set_auth_cookies(
                carrier, new_tokens, self.config, getattr(request.state, "remember_me", False)
            )
            cookies = [(k, v) for k, v in carrier.raw_headers if k == b"set-cookie"]
            message["headers"] = [*message.get("headers", []), *cookies]
            self.logger.info(
                "Tokens refreshed and set in cookies",
                extra={"middleware": "SessionMiddleware", "path": request.url.path},
            )

        await self.forward(request, receive, send, on_start=add_cookies)
