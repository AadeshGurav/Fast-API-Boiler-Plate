"""Main tracing service combining all tracing functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import FastAPI

from app.services.base_service import BaseService
from app.services.tracing.core import TracingCore
from app.services.tracing.decorators import TracingDecorators
from app.services.tracing.exporters import TracingExporters

if TYPE_CHECKING:
    from app.services.logger.core import Logger
    from config import Config


class TracingService(BaseService):
    """Service for distributed tracing using OpenTelemetry.

    Features:
    - Automatic instrumentation for FastAPI, databases, HTTP clients
    - Custom span creation and management
    - Context propagation across services
    - Full logging for tracing events
    """

    def __init__(
        self,
        logger: Logger,
        config: Config,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize tracing service.

        Args:
        ----
            logger: Logger instance.
            config: Configuration dictionary.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        """
        super().__init__(config, logger, *args, **kwargs)
        self.enabled = config.get("tracing_enabled", True)

        # Initialize components
        self.core = TracingCore(config, logger, *args, **kwargs)
        self.decorators = TracingDecorators(logger, self.enabled, self.core.tracer)
        self.exporters = TracingExporters(logger, config, self.enabled)

    def instrument_app(self, app: FastAPI) -> None:
        """Instrument FastAPI application and external clients.

        Args:
        ----
            app: FastAPI application instance.

        """
        self.exporters.instrument_app(app)

    @property
    def span(self):
        """Access to span context manager."""
        return self.decorators.span

    @property
    def database_span(self):
        """Access to database span context manager."""
        return self.decorators.database_span

    @property
    def http_span(self):
        """Access to HTTP span context manager."""
        return self.decorators.http_span

    @property
    def cache_span(self):
        """Access to cache span context manager."""
        return self.decorators.cache_span

    @property
    def measure_time(self):
        """Access to measure_time decorator."""
        return self.decorators.measure_time

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Add an event to the current span.

        Args:
        ----
            name: The name of the event.
            attributes: The attributes of the event.

        """
        self.exporters.add_event(name, attributes)

    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute on the current span.

        Args:
        ----
            key: The key to set.
            value: The value to set.

        """
        self.exporters.set_attribute(key, value)

    def set_attributes(self, attributes: dict[str, Any]) -> None:
        """Set multiple attributes on the current span.

        Args:
        ----
            attributes: The attributes to set.

        """
        self.exporters.set_attributes(attributes)

    def record_exception(self, exception: Exception) -> None:
        """Record an exception in the current span.

        Args:
        ----
            exception: The exception to record.

        """
        self.exporters.record_exception(exception)

    def get_trace_id(self) -> str | None:
        """Get the current trace ID.

        Returns
        -------
            The current trace ID.

        """
        return self.core.get_trace_id()

    def get_span_id(self) -> str | None:
        """Get the current span ID.

        Returns
        -------
            The current span ID.

        """
        return self.core.get_span_id()

    def inject_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """Inject tracing headers for propagation.

        Args:
        ----
            headers: The headers to inject the tracing headers into.

        Returns:
        -------
            The injected headers.

        """
        return self.exporters.inject_headers(headers)

    def extract_context(self, headers: dict[str, str]) -> Any:
        """Extract tracing context from headers.

        Args:
        ----
            headers: The headers to extract the context from.

        Returns:
        -------
            The extracted context.

        """
        return self.exporters.extract_context(headers)

    def close(self) -> None:
        """Close tracing resources (file streams, etc.)."""
        self.core.close()


__all__ = ["TracingService"]
