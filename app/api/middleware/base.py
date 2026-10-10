from __future__ import annotations

import re
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from starlette.datastructures import MutableHeaders
from starlette.requests import Request

if TYPE_CHECKING:
    from collections.abc import Callable

    from starlette.types import ASGIApp, Message, Receive, Scope, Send

    from app.services.logger import Logger
    from config import Config


def path_matches(path: str, patterns: list[str]) -> bool:
    """Whether ``path`` equals, or sits under, any pattern.

    Matching is on whole path segments, so ``/api/v1/auth/login`` covers itself and
    ``/api/v1/auth/login/x`` but never ``/api/v1/auth/login-admin``. ``/`` matches only
    the root (a plain ``startswith("/")`` would make every path match). ``{name}``
    stands for exactly one segment.

    Args:
    ----
        path: Request path.
        patterns: Exact paths or path prefixes, optionally with ``{param}`` segments.

    Returns:
    -------
        True if any pattern matches.

    """
    return _compile_patterns(tuple(patterns)).fullmatch(path) is not None


@lru_cache(maxsize=64)
def _compile_patterns(patterns: tuple[str, ...]) -> re.Pattern[str]:
    """One regex for the whole pattern list (compiled once per distinct list, not per request)."""
    alternatives = [
        "/"
        if pattern == "/"
        else re.sub(r"\\\{[^/]+?\\\}", "[^/]+", re.escape(pattern.rstrip("/"))) + r"(?:/.*)?"
        for pattern in patterns
    ]
    return re.compile("|".join(alternatives) if alternatives else r"(?!)")


class BaseMiddleware:
    """Base for pure-ASGI middleware.

    Starlette's ``BaseHTTPMiddleware`` re-buffers every response through a task and a
    memory stream; this base talks ASGI directly, so there is no extra task per request,
    streaming bodies stay streams, and ``contextvars`` set here reach the route.

    Subclasses implement :meth:`handle`. Helpers:

    * :meth:`forward` runs the rest of the stack and lets you observe or change the
      response *head* (status, headers) as it passes.
    * ``await response(request.scope, receive, send)`` answers without calling the app.
    """

    def __init__(
        self,
        app: ASGIApp,
        config: Config,
        logger: Logger,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.app = app
        self.config = config
        self.logger = logger
        self.exclude_paths: list[str] = []
        for key, value in kwargs.items():
            setattr(self, key, value)

        self.public_paths: list[str] = config["public_paths"]
        self.admin_only_paths: list[str] = config["admin_only_paths"]
        self.initialize(**kwargs)

    def initialize(self, **kwargs: Any) -> None:
        """Hook for subclasses to read configuration."""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI entry point: only HTTP requests on non-excluded paths reach ``handle``."""
        if scope["type"] != "http" or not self.should_process(scope["path"]):
            await self.app(scope, receive, send)
            return
        await self.handle(Request(scope, receive), receive, send)

    async def handle(self, request: Request, receive: Receive, send: Send) -> None:
        """Process one request. Default: pass through."""
        await self.app(request.scope, receive, send)

    async def forward(
        self,
        request: Request,
        receive: Receive,
        send: Send,
        on_start: Callable[[Message], None] | None = None,
    ) -> int | None:
        """Run the rest of the stack.

        ``on_start`` is called with the ``http.response.start`` message before it is sent;
        mutate ``message["headers"]`` (e.g. via :func:`set_headers`) to alter the response.

        Returns:
        -------
            The response status code, or None if no response was started.

        """
        status: int | None = None

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                if on_start:
                    on_start(message)
            await send(message)

        await self.app(request.scope, receive, send_wrapper)
        return status

    def should_process(self, path: str) -> bool:
        """False for paths this middleware is configured to skip."""
        return not path_matches(path, self.exclude_paths) if self.exclude_paths else True

    def is_public_path(self, path: str) -> bool:
        """Whether ``path`` needs no authentication."""
        return path_matches(path, self.public_paths)

    def is_admin_only_path(self, path: str) -> bool:
        """Whether ``path`` is restricted to administrators."""
        return path_matches(path, self.admin_only_paths)


def set_headers(message: Message, values: dict[str, str], *, remove: tuple[str, ...] = ()) -> None:
    """Set (replace) and remove headers on an ``http.response.start`` message."""
    headers = MutableHeaders(scope=message)
    for name in remove:
        if name in headers:
            del headers[name]
    for name, value in values.items():
        headers[name] = value
