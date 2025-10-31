"""Tracing decorators and context managers."""
from __future__ import annotations

import time
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode

from app.services.logger import Logger


class TracingDecorators:
    """Tracing decorators and context managers."""

    def __init__(
        self, logger: Logger, enabled: bool = True, tracer: trace.Tracer = None
    ):
        """Initialize tracing decorators.

        Args:
            logger: Logger instance.
            enabled: Whether tracing is enabled.
            tracer: OpenTelemetry tracer instance.

        """
        self.logger = logger
        self.enabled = enabled
        self.tracer = tracer

    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: dict[str, Any] | None = None,
        record_exception: bool = True,
    ) -> Any:
        """Context manager to create a custom tracing span.

        Args:
            name: The name of the span.
            kind: The kind of the span.
            attributes: The attributes of the span.
            record_exception: Whether to record an exception.

        Returns:
            The span.

        """
        if not self.enabled or not self.tracer:
            yield None
            return

        with self.tracer.start_as_current_span(
            name,
            kind=kind,
            attributes=attributes or {},
            record_exception=record_exception,
        ) as span:
            try:
                self.logger.debug(f"Span started: {name}")
                yield span
            except Exception as e:
                if span and record_exception:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    self.logger.error(f"Exception recorded in span '{name}': {str(e)}")
                raise
            finally:
                self.logger.debug(f"Span ended: {name}")

    @contextmanager
    def database_span(self, operation: str, collection: str, **kwargs) -> Any:
        """Create a span for a database operation.

        Args:
            operation: The operation to create the span for.
            collection: The collection to create the span for.
            **kwargs: The keyword arguments to pass to the span.

        Returns:
            The span.

        """
        attributes = {
            "db.system": kwargs.get("db_system", "mongodb"),
            "db.operation": operation,
            "db.collection": collection,
        }
        if "db_name" in kwargs:
            attributes["db.name"] = kwargs["db_name"]

        with self.span(
            f"db.{operation}", kind=SpanKind.CLIENT, attributes=attributes
        ) as s:
            yield s

    @contextmanager
    def http_span(self, method: str, url: str, **kwargs) -> Any:
        """Create a span for an HTTP operation.

        Args:
            method: The HTTP method.
            url: The HTTP URL.
            **kwargs: The keyword arguments to pass to the span.

        Returns:
            The span.

        """
        attributes = {
            "http.method": method,
            "http.url": url,
            "http.scheme": kwargs.get("scheme", "https"),
        }
        if "status_code" in kwargs:
            attributes["http.status_code"] = kwargs["status_code"]

        with self.span(
            f"http.{method}", kind=SpanKind.CLIENT, attributes=attributes
        ) as s:
            yield s

    @contextmanager
    def cache_span(self, operation: str, key: str, **kwargs) -> Any:
        """Create a span for cache operations.

        Args:
            operation: The operation to create the span for.
            key: The key to create the span for.
            **kwargs: The keyword arguments to pass to the span.

        Returns:
            The span.

        """
        attributes = {
            "cache.operation": operation,
            "cache.key": key,
            "cache.system": kwargs.get("cache_system", "redis"),
        }
        with self.span(
            f"cache.{operation}", kind=SpanKind.CLIENT, attributes=attributes
        ) as s:
            yield s

    def measure_time(
        self, span_name: str, attributes: dict[str, Any] | None = None
    ) -> Callable:
        """Decorator to measure execution time of a function and create a span.

        Args:
            span_name: The name of the span.
            attributes: The attributes to set on the span.

        Returns:
            The decorator.

        """

        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                with self.span(span_name or func.__name__, attributes=attributes) as s:
                    try:
                        result = func(*args, **kwargs)
                        if s:
                            s.set_attribute(
                                "duration_ms", (time.time() - start_time) * 1000
                            )
                        return result
                    except Exception as e:
                        if s:
                            s.set_attribute("error", True)
                            s.set_attribute(
                                "duration_ms", (time.time() - start_time) * 1000
                            )
                        self.logger.error(
                            f"Exception in measured function '{func.__name__}': {e}"
                        )
                        raise

            return wrapper

        return decorator


__all__ = ["TracingDecorators"]
__all__ = ["TracingDecorators"]
