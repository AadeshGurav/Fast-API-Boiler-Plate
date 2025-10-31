"""Error handling and logging service for the application."""

from __future__ import annotations

import traceback
from typing import TYPE_CHECKING, Any

from fastapi import status
from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from fastapi import HTTPException

    from app.services.error.exceptions import AppExceptionError
    from app.services.logger import Logger
    from config import Config


class ErrorService:
    """Service to handle exceptions and provide consistent logging and HTTP responses."""

    def __init__(self: ErrorService, logger: Logger, config: Config) -> None:
        """Initialize the ErrorService.

        Args:
        ----
        logger: Logger instance for error logging.
        config: Application configuration.

        Returns:
        -------
            None

        """
        self.logger = logger
        self.config = config
        self.debug = config.get("app_debug", False)

    def log_exception(
        self: ErrorService, exc: Exception, extra: dict | None = None
    ) -> str:
        """Log an exception and optionally send it to Sentry.

        Args:
        ----
            exc: The exception to log.
            extra: Optional extra context to include in logs.  # noqa: E501

        Returns:
        -------
            Formatted traceback string.

        """
        tb: str = traceback.format_exc()
        self.logger.error(f"Exception occurred: {str(exc)}", exc_info=True, extra=extra)

        # Capture exception in Sentry if available
        # try:
        #     if sentry_service and sentry_service.is_enabled():
        #         sentry_service.capture_exception(exc, extra=extra)
        #         self.logger.debug("Exception captured in Sentry")
        # except Exception as sentry_error:  # noqa: BLE001
        #     self.logger.warning(f"Failed to capture exception in Sentry: {sentry_error}")

        return tb

    def format_error(
        self: ErrorService,
        exc: Exception,
        user_message: str | None = None,
    ) -> dict[str, Any]:
        """Format an exception for HTTP response.

        Args:
        ----
            exc: Exception instance to format.
            user_message: Optional message to show to the user.

        Returns:
        -------
            A dictionary containing error details.

        """
        developer_message: str | None = str(exc) if self.debug else None

        if isinstance(exc, AppExceptionError):
            return {
                "error": exc.code,
                "message": user_message or exc.message,
                "details": exc.details,
                "developer_message": developer_message,
            }
        if isinstance(exc, HTTPException):
            return {
                "error": "http_error",
                "message": user_message or exc.detail,
                "details": None,
                "developer_message": developer_message,
            }

        return {
            "error": "internal_error",
            "message": user_message or "An unexpected error occurred.",
            "details": None,
            "developer_message": developer_message,
        }

    def http_response(
        self: ErrorService,
        exc: Exception,
        user_message: str | None = None,
        status_code: int | None = None,
    ) -> JSONResponse:
        """Build a JSONResponse for an exception.

        Args:
        ----
            exc: The exception to respond with.
            user_message: Optional user-facing message.
            status_code: Optional override HTTP status code.

        Returns:
        -------
            JSONResponse with formatted error.

        """
        if isinstance(exc, AppExceptionError):
            code = exc.status_code
        elif isinstance(exc, HTTPException):
            code = exc.status_code
        else:
            code = status.HTTP_500_INTERNAL_SERVER_ERROR

        if status_code is not None:
            code = status_code

        response_content = self.format_error(exc, user_message)
        self.logger.debug(f"Formatted HTTP error response: {response_content}")
        return JSONResponse(status_code=code, content=response_content)
