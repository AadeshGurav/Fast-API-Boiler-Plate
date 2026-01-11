"""Tracing exporters and instrumentation."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

from app.services.logger import Logger


class TracingExporters:
    """Tracing exporters and instrumentation functionality."""

    def __init__(self, logger: Logger, enabled: bool = True):
        """Initialize tracing exporters.

        Args:
        ----
            logger: Logger instance.
            enabled: Whether tracing is enabled.

        """
        self.logger = logger
        self.enabled = enabled

    def instrument_app(self, app: FastAPI) -> None:
        """Instrument FastAPI application and external clients.

        Args:
        ----
            app: FastAPI application instance.

        """
        if not self.enabled:
            self.logger.info("Tracing disabled; skipping instrumentation")
            return

        try:
            FastAPIInstrumentor.instrument_app(
                app,
                tracer_provider=trace.get_tracer_provider(),
                excluded_urls="/health,/ready,/metrics",
            )
            HTTPXClientInstrumentor().instrument()
            # Optionally instrument PyMongo; default disabled to avoid attribute type issues
            if app.state.config.get("tracing_pymongo_enabled", False):
                try:
                    PymongoInstrumentor().instrument()
                except Exception as pymongo_instr_error:  # noqa: BLE001
                    # Log but don't fail - PyMongo instrumentation may have attribute type issues
                    self.logger.warning(
                        f"PyMongo instrumentation failed (non-critical): {pymongo_instr_error}. "
                        "Continuing without PyMongo tracing."
                    )
            RedisInstrumentor().instrument()
            self.logger.info("Application successfully instrumented for tracing")
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Failed to instrument application: {str(e)}")
            # If instrumentation fails, log but don't crash
            self.logger.warning("Continuing without full tracing instrumentation")

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Add an event to the current span.

        Args:
        ----
            name: The name of the event.
            attributes: The attributes of the event.

        """
        if not self.enabled:
            return

        current_span = trace.get_current_span()
        if current_span:
            current_span.add_event(name, attributes=attributes or {})
            self.logger.debug(f"Event added to span '{current_span.name}': {name}")

    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute on the current span.

        Args:
        ----
            key: The key to set.
            value: The value to set.

        """
        if not self.enabled:
            return

        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute(key, value)
            self.logger.debug(
                f"Attribute set on span '{current_span.name}': {key}={value}"
            )

    def set_attributes(self, attributes: dict[str, Any]) -> None:
        """Set multiple attributes on the current span.

        Args:
        ----
            attributes: The attributes to set.

        """
        if not self.enabled:
            return

        current_span = trace.get_current_span()
        if current_span:
            for key, value in attributes.items():
                current_span.set_attribute(key, value)
            self.logger.debug(
                f"Multiple attributes set on span '{current_span.name}': {attributes}"
            )

    def record_exception(self, exception: Exception) -> None:
        """Record an exception in the current span.

        Args:
        ----
            exception: The exception to record.

        """
        if not self.enabled:
            return

        current_span = trace.get_current_span()
        if current_span:
            current_span.record_exception(exception)
            from opentelemetry.trace import Status, StatusCode

            current_span.set_status(Status(StatusCode.ERROR, str(exception)))
            self.logger.error(
                f"Exception recorded in span '{current_span.name}': {exception}"
            )

    def inject_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """Inject tracing headers for propagation.

        Args:
        ----
            headers: The headers to inject the tracing headers into.

        Returns:
        -------
            The injected headers.

        """
        if not self.enabled:
            return headers

        from opentelemetry.propagators import inject

        inject(headers)
        self.logger.debug(f"Tracing headers injected: {headers}")
        return headers

    def extract_context(self, headers: dict[str, str]) -> Any:
        """Extract tracing context from headers.

        Args:
        ----
            headers: The headers to extract the context from.

        Returns:
        -------
            The extracted context.

        """
        if not self.enabled:
            return None

        from opentelemetry.propagators import extract

        ctx = extract(headers)
        self.logger.debug(f"Tracing context extracted from headers: {headers}")
        return ctx


__all__ = ["TracingExporters"]
__all__ = ["TracingExporters"]
