"""Sentry service for error tracking and performance monitoring.

Provides comprehensive error tracking, performance monitoring, and session tracking
using Sentry SDK with FastAPI integration.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.pymongo import PyMongoIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.services.base_service import BaseService

if TYPE_CHECKING:
    from app.services.logger import Logger
    from config import Config


class SentryService(BaseService):
    """Service for Sentry error tracking and performance monitoring.

    Features:
    - Error tracking with context and breadcrumbs
    - Performance monitoring with traces
    - Session tracking
    - Custom before_send filtering
    - Integration with FastAPI, databases, and HTTP clients
    - Environment-specific configuration
    """

    def __init__(
        self: SentryService,
        config: Config,
        logger: Logger,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize the SentryService.

        Args:
        ----
            logger: The logger to use.
            config: The configuration to use.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
        -------
            None

        """
        super().__init__(config, logger, *args, **kwargs)

        self.enabled: bool = bool(config.get("sentry_dsn"))
        self.dsn: str = config.get("sentry_dsn")
        self.environment: str = config.get("sentry_environment", "development")
        self.traces_sample_rate: float = config.get("sentry_traces_sample_rate", 1.0)
        self.profiles_sample_rate: float = config.get(
            "sentry_profiles_sample_rate", 1.0
        )
        self.enable_performance_monitoring: bool = config.get(
            "sentry_enable_performance_monitoring", True
        )
        self.enable_session_tracking: bool = config.get(
            "sentry_enable_session_tracking", True
        )
        self.before_send_function: Callable | None = config.get("sentry_before_send")

    def _initialize_sentry(self) -> None:
        """Initialize Sentry SDK with configuration."""
        try:
            # Get before_send function if specified
            before_send = None
            if self.before_send_function:
                before_send = self._get_before_send_function()

            # Configure integrations
            integrations = [
                FastApiIntegration(),
                RedisIntegration(),
                SqlalchemyIntegration(),
                HttpxIntegration(),
                PyMongoIntegration(),
            ]

            # Initialize Sentry
            sentry_sdk.init(
                dsn=self.dsn,
                environment=self.environment,
                traces_sample_rate=self.traces_sample_rate,
                profiles_sample_rate=self.profiles_sample_rate,
                enable_tracing=self.enable_performance_monitoring,
                before_send=before_send,
                integrations=integrations,
                # Additional configuration
                release=self.config.get("app_version", "1.0.0"),
                debug=self.config.get("app_debug", False),
                # Set user context from request if available
                send_default_pii=False,  # Don't send PII by default
            )

            self.logger.info(
                f"Sentry initialized for environment '{self.environment}'",
                extra={
                    "sentry_dsn": self._mask_dsn(self.dsn),
                    "traces_sample_rate": self.traces_sample_rate,
                    "profiles_sample_rate": self.profiles_sample_rate,
                },
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize Sentry: {str(e)}")
            self.enabled = False

    def _get_before_send_function(self) -> Callable | None:
        """Get the before_send function if specified in config."""
        if not self.before_send_function:
            return None

        try:
            # Import the function dynamically
            module_name, function_name = self.before_send_function.rsplit(".", 1)
            module = __import__(module_name, fromlist=[function_name])
            return getattr(module, function_name)
        except Exception as e:
            self.logger.warning(
                f"Could not load before_send function '{self.before_send_function}': {e}"
            )
            return None

    def _mask_dsn(self, dsn: str) -> str:
        """Mask DSN for logging (show only project and public key)."""
        if not dsn:
            return "None"

        try:
            # DSN format: https://public_key@host/project_id
            parts = dsn.split("@")
            if len(parts) == 2:
                public_key = parts[0].split("//")[1]
                host_project = parts[1].split("/")
                if len(host_project) == 2:
                    return f"https://{public_key[:8]}...@{host_project[0]}/{host_project[1]}"
        except Exception:
            pass

        return "***masked***"

    def capture_exception(self, exception: Exception, **kwargs) -> str | None:
        """Capture an exception in Sentry."""
        if not self.enabled:
            return None

        try:
            return sentry_sdk.capture_exception(exception, **kwargs)
        except Exception as e:
            self.logger.error(f"Failed to capture exception in Sentry: {e}")
            return None

    def capture_message(
        self, message: str, level: str = "info", **kwargs
    ) -> str | None:
        """Capture a message in Sentry."""
        if not self.enabled:
            return None

        try:
            return sentry_sdk.capture_message(message, level=level, **kwargs)
        except Exception as e:
            self.logger.error(f"Failed to capture message in Sentry: {e}")
            return None

    def set_user(
        self,
        user_id: str,
        email: str | None = None,
        username: str | None = None,
        **kwargs,
    ) -> None:
        """Set user context for Sentry."""
        if not self.enabled:
            return

        try:
            sentry_sdk.set_user(
                {"id": user_id, "email": email, "username": username, **kwargs}
            )
        except Exception as e:
            self.logger.error(f"Failed to set user in Sentry: {e}")

    def set_tag(self, key: str, value: str) -> None:
        """Set a tag in Sentry."""
        if not self.enabled:
            return

        try:
            sentry_sdk.set_tag(key, value)
        except Exception as e:
            self.logger.error(f"Failed to set tag in Sentry: {e}")

    def set_context(self, name: str, data: dict[str, Any]) -> None:
        """Set context data in Sentry."""
        if not self.enabled:
            return

        try:
            sentry_sdk.set_context(name, data)
        except Exception as e:
            self.logger.error(f"Failed to set context in Sentry: {e}")

    def add_breadcrumb(
        self, message: str, category: str = "info", level: str = "info", **kwargs
    ) -> None:
        """Add a breadcrumb to Sentry."""
        if not self.enabled:
            return

        try:
            sentry_sdk.add_breadcrumb(
                message=message, category=category, level=level, **kwargs
            )
        except Exception as e:
            self.logger.error(f"Failed to add breadcrumb in Sentry: {e}")

    def start_transaction(
        self, name: str, operation: str = "http.server", **kwargs
    ) -> Any:
        """Start a performance transaction."""
        if not self.enabled or not self.enable_performance_monitoring:
            return None

        try:
            return sentry_sdk.start_transaction(
                name=name, operation=operation, **kwargs
            )
        except Exception as e:
            self.logger.error(f"Failed to start transaction in Sentry: {e}")
            return None

    def set_extra(self, key: str, value: Any) -> None:
        """Set extra data in Sentry."""
        if not self.enabled:
            return

        try:
            sentry_sdk.set_extra(key, value)
        except Exception as e:
            self.logger.error(f"Failed to set extra in Sentry: {e}")

    def flush(self, timeout: float | None = None) -> None:
        """Flush Sentry events."""
        if not self.enabled:
            return

        try:
            sentry_sdk.flush(timeout=timeout)
        except Exception as e:
            self.logger.error(f"Failed to flush Sentry: {e}")

    def get_current_hub(self):
        """Get the current Sentry hub."""
        if not self.enabled:
            return None

        try:
            return sentry_sdk.Hub.current
        except Exception as e:
            self.logger.error(f"Failed to get Sentry hub: {e}")
            return None

    def is_enabled(self) -> bool:
        """Check if Sentry is enabled."""
        return self.enabled
