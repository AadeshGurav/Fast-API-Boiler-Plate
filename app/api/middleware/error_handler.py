"""Error handler middleware for FastAPI.

Handles exceptions, logs them with context, and generates proper HTTP responses.
"""

from __future__ import annotations

import traceback
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.api.middleware.base import BaseMiddleware
from app.api.middleware.serialization import JSONEncoder
from app.services.error.error_service import ErrorService
from app.services.logger import create_log_context


class ErrorHandlerMiddleware(BaseMiddleware):
    """Middleware for handling and logging errors."""

    def initialize(self: ErrorHandlerMiddleware, **kwargs) -> None:
        """Initialize error handler middleware.

        Args:
        ----
            config: Optional dictionary of configuration values.
                Expected keys:
                    - log_errors (bool)
                    - include_traceback (bool)
                    - app_debug (bool)
            kwargs: Additional keyword arguments.

        """
        self.log_errors: bool = self.config.get("log_errors", True)
        self.include_traceback: bool = self.config.get("include_traceback", False)
        self.app_debug: bool = self.config.get("app_debug", False)
        self.error_service: ErrorService | None = None

        # Try to import a centralized error service if available
        try:
            self.error_service = self.app.state.error_service
        except AttributeError as e:
            self.logger.warning(
                f"Error service not found: {e}",
                extra={"middleware": "ErrorHandlerMiddleware"},
            )

        self.logger.info(
            "ErrorHandlerMiddleware initialized",
            extra={
                "log_errors": self.log_errors,
                "include_traceback": self.include_traceback,
                "app_debug": self.app_debug,
                "middleware": "ErrorHandlerMiddleware",
            },
        )

    async def process_request(
        self: ErrorHandlerMiddleware, request: Request, call_next: Callable
    ) -> Response:
        """Process request with error handling.

        Args:
        ----
            request: The incoming HTTP request.
            call_next: The next callable in the middleware chain.

        Returns:
        -------
            The HTTP response.

        """
        try:
            response = await call_next(request)
            return response

        except Exception as exc:  # noqa: BLE001
            if self.log_errors:
                self._log_error(exc, request)

            if self.error_service:
                return self.error_service.http_response(exc)

            return self._create_error_response(exc)

    def _log_error(
        self: ErrorHandlerMiddleware, exc: Exception, request: Request
    ) -> None:
        """Log error with context.

        Args:
        ----
            exc: The exception object.
            request: The incoming HTTP request.

        """
        try:
            logger = getattr(self, "logger", None)
            if logger:
                logger.error(
                    f"Unhandled exception: {exc}",
                    extra=create_log_context(
                        method=request.method,
                        path=request.url.path,
                        client_ip=request.client.host if request.client else "unknown",
                        user_agent=request.headers.get("user-agent", "unknown"),
                        traceback=traceback.format_exc()
                        if self.include_traceback
                        else None,
                        middleware="ErrorHandlerMiddleware",
                    ),
                    exc_info=True,
                )
        except Exception as log_exc:  # noqa: BLE001
            # Ensure logging failure does not break the application
            if logger:
                logger.error(
                    f"Failed to log error: {log_exc}",
                    extra=create_log_context(middleware="ErrorHandlerMiddleware"),
                )

    def _create_error_response(
        self: ErrorHandlerMiddleware, exc: Exception
    ) -> JSONResponse:
        """Create a standardized JSON error response.

        Args:
        ----
            exc: The exception object.

        Returns:
        -------
            JSONResponse with HTTP 500 status.

        """
        error_content: dict[str, any] = {
            "error": "internal_error",
            "message": "An unexpected error occurred.",
        }

        if self.app_debug:
            error_content.update(
                {
                    "developer_message": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )

        # Serialize datetime objects and other non-JSON-serializable types
        serialized_content = JSONEncoder.serialize(error_content)

        return JSONResponse(status_code=500, content=serialized_content)
