"""Template context middleware for FastAPI."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from fastapi import Request, Response

from app.services.logger import create_log_context

from .base import BaseMiddleware


class TemplateContextMiddleware(BaseMiddleware):
    """Middleware to add common template context data to all requests."""

    def initialize(
        self: TemplateContextMiddleware,
        **kwargs,
    ) -> None:
        """Initialize template context middleware.

        Args:
        ----
            kwargs: Additional keyword arguments.

        """
        self.logger.info(
            "TemplateContextMiddleware initialized",
            extra=create_log_context(middleware="TemplateContextMiddleware"),
        )

    async def process_request(
        self: TemplateContextMiddleware, request: Request, call_next: Callable
    ) -> Response:
        """Add common template context to the request state.

        Args:
        ----
            request: Incoming HTTP request
            call_next: Next callable in middleware chain

        Returns:
        -------
            Response object

        """
        try:
            template_context = {
                "request": request,
                "now": datetime.now,
                "timedelta": timedelta,
                "config": self.config,
                "app_name": self.config.get("app_title", "FastAPI App"),
                "version": "1.0.0",
                "debug": self.config.get("app_debug", False),
                "site_name": self.config.get("app_title", "FastAPI App"),
            }

            request.state.template_context = template_context

        except Exception as exc:  # noqa: BLE001
            # Fail gracefully and continue request processing
            self.logger.warning(
                f"TemplateContextMiddleware failed: {exc}",
                extra=create_log_context(middleware="TemplateContextMiddleware"),
            )

        # Continue processing the request
        response = await call_next(request)
        return response
