"""Error handling and logging service for the application."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from fastapi.exceptions import RequestValidationError
from starlette import status
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from app.cache import CacheUnavailableError
from app.services.base_service import BaseService
from app.services.error.exceptions import AppExceptionError

if TYPE_CHECKING:
    from app.services.logger import Logger
    from config import Config

PROBLEM_JSON = "application/problem+json"


class ErrorService(BaseService):
    """Service to handle exceptions and provide consistent logging and HTTP responses."""

    def __init__(
        self: ErrorService,
        logger: Logger,
        config: Config,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize the ErrorService.

        Args:
        ----
            logger: Logger instance for error logging.
            config: Application configuration.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
        -------
            None

        """
        super().__init__(config, logger, *args, **kwargs)
        self.debug = config["app_debug"]

    def format_error(
        self: ErrorService,
        exc: Exception,
        user_message: str | None = None,
        status_code: int | None = None,
        instance: str | None = None,
    ) -> dict[str, Any]:
        """Describe an exception as an RFC 9457 problem document.

        Internal exception text is only included in debug mode (``developer_message``);
        unexpected errors always show a generic message to the caller.

        Args:
        ----
            exc: Exception instance to format.
            user_message: Optional message to show to the user.
            status_code: HTTP status of the response.
            instance: Request path the problem occurred on.

        Returns:
        -------
            A problem-details dictionary.

        """
        if isinstance(exc, AppExceptionError):
            code, detail, extra = exc.code, exc.message, {"details": exc.details}
            status_code = status_code or exc.status_code
        elif isinstance(exc, HTTPException):
            code, detail, extra = "http_error", exc.detail, {}
            status_code = status_code or exc.status_code
        elif isinstance(exc, RequestValidationError):
            code, detail = "validation_error", "The request is invalid."
            extra = {"errors": jsonable_validation_errors(exc)}
            status_code = status_code or status.HTTP_422_UNPROCESSABLE_ENTITY
        elif isinstance(exc, CacheUnavailableError):
            code, extra = "dependency_unavailable", {}
            detail = "A required service is temporarily unavailable. Try again shortly."
            status_code = status_code or status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            code, detail, extra = "internal_error", "An unexpected error occurred.", {}
            status_code = status_code or status.HTTP_500_INTERNAL_SERVER_ERROR

        problem: dict[str, Any] = {
            "type": "about:blank",
            "title": HTTPStatus(status_code).phrase,
            "status": status_code,
            "detail": user_message or detail,
            "code": code,
            **{k: v for k, v in extra.items() if v is not None},
        }
        if instance:
            problem["instance"] = instance
        if self.debug and not isinstance(exc, (AppExceptionError, HTTPException)):
            problem["developer_message"] = str(exc)
        return problem

    def http_response(
        self: ErrorService,
        exc: Exception,
        user_message: str | None = None,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
        instance: str | None = None,
    ) -> JSONResponse:
        """Build an ``application/problem+json`` response for an exception.

        Args:
        ----
            exc: The exception to respond with.
            user_message: Optional user-facing message.
            status_code: Optional override HTTP status code.
            headers: Extra response headers (e.g. ``WWW-Authenticate``).
            instance: Request path the problem occurred on.

        Returns:
        -------
            JSONResponse with the problem document.

        """
        problem = self.format_error(exc, user_message, status_code, instance)
        return JSONResponse(
            status_code=problem["status"],
            content=problem,
            media_type=PROBLEM_JSON,
            headers=headers,
        )


def jsonable_validation_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    """Validation errors without the submitted input (it may contain passwords)."""
    return [
        {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
