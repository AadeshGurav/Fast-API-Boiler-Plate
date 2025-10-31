from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.uitls import extract_device_info

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import Request, Response
    from starlette.types import ASGIApp

    from app.models.session import DeviceInfo
    from app.services.logger import Logger
    from config import Config


class BaseMiddleware(BaseHTTPMiddleware):
    """Base middleware class with common functionality for all middleware."""

    def __init__(
        self: BaseMiddleware,
        app: ASGIApp,
        config: Config | None = None,
        logger: Logger | None = None,
        exclude_paths: list[str] | None = None,
        public_paths: list[str] | None = None,
        admin_only_paths: list[str] | None = None,
        role_permissions: dict[str, list[str]] | None = None,
        **kwargs,
    ) -> None:
        """Initialize the base middleware.

        Args:
        ----
            app: The ASGI application.
            config: The configuration.
            logger: The logger.
            exclude_paths: The paths to exclude.
            public_paths: The paths to public.
            admin_only_paths: The paths to admin-only.
            role_permissions: The role permissions.
            kwargs: Additional keyword arguments.

        Returns:
        -------
            The base middleware.

        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or []
        self.kwargs = kwargs

        self.config = config
        self.logger = logger

        # Common paths and permissions
        self.public_paths = public_paths or self.config.get(
            "public_paths",
            ["/", "/docs", "/redoc", "/openapi.json"],
        )

        self.admin_only_paths = admin_only_paths or self.config.get(
            "admin_only_paths",
            ["/admin", "/users/list", "/users/{id}/permissions", "/users/{id}/role"],
        )

        self.role_permissions = role_permissions or self.config.get(
            "role_permissions",
            {
                "admin": ["*"],
                "manager": ["read", "write", "update"],
                "user": ["read", "write"],
                "guest": ["read"],
            },
        )

        # Initialize the middleware
        self.initialize(**kwargs)

    def initialize(self: BaseMiddleware, **kwargs) -> None:
        """Initialize middleware with specific configuration.
        Override this in subclasses to handle specific initialization.

        Args:
        ----
            kwargs: Additional keyword arguments.

        Returns:
        -------
            None

        """
        pass

    def should_process_request(self: BaseMiddleware, request: Request) -> bool:
        """Determine if the middleware should process this request based on path.

        Args:
        ----
            request: The request to check.

        Returns:
        -------
            True if the middleware should process this request, False otherwise.

        """
        if not self.exclude_paths:
            return True

        path = request.url.path
        return not any(path.startswith(excluded) for excluded in self.exclude_paths)

    def is_public_path(self: BaseMiddleware, path: str) -> bool:
        """Check if path is public (doesn't require authentication).

        Args:
        ----
            path: The path to check.

        Returns:
        -------
            True if path is public, False otherwise.

        """
        return any(path.startswith(p) for p in self.public_paths)

    def is_admin_only_path(self: BaseMiddleware, path: str) -> bool:
        """Check if path is admin-only.

        Args:
        ----
            path: The path to check.

        Returns:
        -------
            True if path is admin-only, False otherwise.

        """
        return any(path.startswith(p.split("{")[0]) for p in self.admin_only_paths)

    async def dispatch(
        self: BaseMiddleware, request: Request, call_next: Callable
    ) -> Response:
        """Default dispatch method that implements path exclusion logic.

        Args:
        ----
            request: The request to process.
            call_next: The next middleware to call.

        Returns:
        -------
            The response from the next middleware.

        """
        if not self.should_process_request(request):
            return await call_next(request)

        return await self.process_request(request, call_next)

    async def process_request(
        self: BaseMiddleware, request: Request, call_next: Callable
    ) -> Response:
        """Process the request. Override in subclasses.

        Args:
        ----
            request: The request to process.
            call_next: The next middleware to call.

        Returns:
        -------
            The response from the next middleware.

        """
        return await call_next(request)

    def _extract_device_info(self: BaseMiddleware, request: Request) -> DeviceInfo:
        """Extract device information from request.

        Args:
        ----
            request: The request to extract device information from.

        Returns:
        -------
            The device information.

        """
        return extract_device_info(request)
