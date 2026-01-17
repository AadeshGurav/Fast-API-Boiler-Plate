"""Sentry integration middleware for FastAPI using BaseMiddleware."""

from __future__ import annotations

import time
from collections.abc import Callable

from fastapi import Request, Response

from app.services.logger import create_log_context
from app.utils.service_utils import is_service_enabled

from .base import BaseMiddleware


class SentryMiddleware(BaseMiddleware):
    """Middleware to integrate Sentry with FastAPI.

    Features:
    - Automatic exception capture
    - Request/response breadcrumbs
    - User and endpoint context
    - Performance monitoring
    - Safe failure handling
    """

    def initialize(
        self: SentryMiddleware,
        **kwargs,
    ) -> None:
        """Initialize Sentry middleware with configuration.

        Args:
        ----
            kwargs: Additional keyword arguments.

        """
        self.capture_exceptions = self.config.get("capture_exceptions", True)
        self.capture_requests = self.config.get("capture_requests", True)
        self.set_user_context = self.config.get("set_user_context", True)
        self.logger.info(
            "SentryMiddleware initialized",
            extra=create_log_context(middleware="SentryMiddleware"),
        )

    async def process_request(
        self: SentryMiddleware, request: Request, call_next: Callable
    ) -> Response:
        """Process request and integrate Sentry monitoring.

        Args:
        ----
            request: Incoming HTTP request
            call_next: Next callable in middleware chain

        Returns:
        -------
            Response object

        """
        if not is_service_enabled(self.sentry_service, "sentry_service", self.config):
            return await call_next(request)

        start_time = time.time()
        self._set_request_context(request)

        try:
            response = await call_next(request)

            if self.capture_requests:
                self._add_response_breadcrumb(request, response, start_time)

            return response

        except Exception as exc:
            if self.capture_exceptions:
                self._capture_exception(exc, request, start_time)
            raise

    def _set_request_context(self: SentryMiddleware, request: Request) -> None:
        """Set request-level context for Sentry.

        Args:
        ----
            request: Incoming HTTP request

        """
        if not self.sentry_service:
            return

        try:
            self.sentry_service.set_context(
                "request",
                {
                    "method": request.method,
                    "url": str(request.url),
                    "headers": dict(request.headers),
                    "client_ip": request.client.host if request.client else "unknown",
                },
            )

            if self.set_user_context:
                self._set_user_context(request)

        except Exception as exc:  # noqa: BLE001
            if hasattr(self, "logger"):
                self.logger.warning(
                    f"Sentry request context failed: {exc}",
                    extra=create_log_context(middleware="SentryMiddleware"),
                )

    def _set_user_context(self: SentryMiddleware, request: Request) -> None:
        """Set user context and tags for Sentry.

        Args:
        ----
            request: Incoming HTTP request

        """
        if not self.sentry_service:
            return

        try:
            user_id = getattr(request.state, "user_id", None)
            if user_id:
                self.sentry_service.set_user(
                    user_id=user_id,
                    username=getattr(request.state, "username", None),
                    email=getattr(request.state, "email", None),
                )

            self.sentry_service.set_tag("endpoint", request.url.path)
            self.sentry_service.set_tag("method", request.method)

        except Exception as exc:  # noqa: BLE001
            if hasattr(self, "logger"):
                self.logger.warning(
                    f"Sentry user context failed: {exc}",
                    extra={"middleware": "SentryMiddleware"},
                )

    def _add_response_breadcrumb(
        self: SentryMiddleware,
        request: Request,
        response: Response,
        start_time: float,
    ) -> None:
        """Add breadcrumb for request-response in Sentry.

        Args:
        ----
            request: Incoming HTTP request
            response: HTTP response
            start_time: Request start timestamp

        """
        if not self.sentry_service:
            return

        try:
            duration = time.time() - start_time
            self.sentry_service.add_breadcrumb(
                message=f"Response: {request.method} {request.url.path}",
                category="http",
                level="info",
                data={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_seconds": duration,
                    "content_length": response.headers.get("content-length", "unknown"),
                },
            )
        except Exception as exc:  # noqa: BLE001
            if hasattr(self, "logger"):
                self.logger.warning(
                    f"Sentry breadcrumb addition failed: {exc}",
                    extra={"middleware": "SentryMiddleware"},
                )

    def _capture_exception(
        self: SentryMiddleware, exc: Exception, request: Request, start_time: float
    ) -> None:
        """Capture an exception in Sentry with additional request context.

        Args:
        ----
            exc: Exception instance
            request: Incoming HTTP request
            start_time: Request start timestamp

        """
        if not self.sentry_service:
            return

        try:
            duration = time.time() - start_time
            extra = {
                "request_method": request.method,
                "request_path": request.url.path,
                "request_duration": duration,
                "request_id": getattr(request.state, "request_id", "unknown"),
            }
            self.sentry_service.capture_exception(exc, extra=extra)
        except Exception as e:  # noqa: BLE001
            if hasattr(self, "logger"):
                self.logger.warning(
                    f"Sentry exception capture failed: {e}",
                    extra={"middleware": "SentryMiddleware"},
                )
