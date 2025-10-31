from __future__ import annotations

from typing import Any


class AppExceptionError(Exception):
    """Base exception for application errors."""

    def __init__(
        self: AppExceptionError,
        message: str,
        code: str | None = None,
        status_code: int = 500,
        details: Any = None,
    ) -> None:
        """Initialize the AppExceptionError.

        Args:
        ----
            message: Human-readable error message.
            code: Optional application-specific error code.
            status_code: HTTP status code.
            details: Additional debug information.

        Returns:
        -------
            None

        """
        super().__init__(message)
        self.message: str = message
        self.code: str = code or "app_error"
        self.status_code: int = status_code
        self.details: Any = details


class UserFacingExceptionError(AppExceptionError):
    """Exception for errors that should be shown to end users."""

    def __init__(
        self: UserFacingExceptionError,
        message: str,
        code: str | None = None,
        status_code: int = 400,
        details: Any = None,
    ) -> None:
        """Initialize the UserFacingExceptionError.

        Args:
        ----
            message: Human-readable error message.
            code: Optional application-specific error code.
            status_code: HTTP status code.
            details: Additional debug information.

        Returns:
        -------
            None

        """
        super().__init__(message, code, status_code, details)


class RetryExhaustedError(AppExceptionError):
    """Raised when all retry attempts are exhausted."""

    def __init__(
        self: RetryExhaustedError, message: str, last_exception: Exception | None = None
    ) -> None:
        """Initialize the RetryExhausted exception.

        Args:
        ----
            message: The message to display.
            last_exception: The last exception that occurred.

        Returns:
        -------
            None

        """
        super().__init__(message)
        self.last_exception: Exception | None = last_exception
