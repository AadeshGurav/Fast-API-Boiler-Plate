"""Metrics decorators and context managers."""

from __future__ import annotations

import time
from functools import wraps
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType

    from app.services.logger import Logger
    from app.services.metrics.base import MetricsService


T = TypeVar("T")


class MetricsDecorators:
    """Decorators for automatic metrics collection."""

    def __init__(
        self: MetricsDecorators, metrics_service: MetricsService, logger: Logger
    ) -> None:
        """Initialize metrics decorators.

        Args:
        ----
            metrics_service: The metrics service instance.
            logger: The logger to use.

        """
        self.metrics_service: MetricsService = metrics_service
        self.logger: Logger = logger

    def time_function(
        self: MetricsDecorators,
        function_name: str | None = None,
        labels: dict[str, str] | None = None,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """Decorator to time function execution.

        Args:
        ----
            function_name: Custom function name for metrics.
            labels: Additional labels for metrics.

        Returns:
        -------
            Decorator function.

        """

        def decorator(
            func: Callable[..., T],
        ) -> Callable[[Callable[..., T]], Callable[..., T]]:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                if not self.metrics_service.enabled:
                    return func(*args, **kwargs)

                name = function_name or f"{func.__module__}.{func.__name__}"
                start_time = time.time()

                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time

                    # Record success metrics
                    self.metrics_service.observe_histogram(
                        "function_duration_seconds",
                        duration,
                        {**(labels or {}), "function": name, "status": "success"},
                    )

                    return result

                except Exception as e:
                    duration = time.time() - start_time

                    # Record error metrics
                    self.metrics_service.observe_histogram(
                        "function_duration_seconds",
                        duration,
                        {**(labels or {}), "function": name, "status": "error"},
                    )

                    self.metrics_service.record_error(
                        error_type=type(e).__name__,
                        component=name,
                    )

                    raise

            return wrapper

        return decorator

    def count_calls(
        self: MetricsDecorators,
        function_name: str | None = None,
        labels: dict[str, str] | None = None,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """Decorator to count function calls.

        Args:
        ----
            function_name: Custom function name for metrics.
            labels: Additional labels for metrics.

        Returns:
        -------
            Decorator function.

        """

        def decorator(
            func: Callable[..., T],
        ) -> Callable[[Callable[..., T]], Callable[..., T]]:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                if not self.metrics_service.enabled:
                    return func(*args, **kwargs)

                name = function_name or f"{func.__module__}.{func.__name__}"

                try:
                    result = func(*args, **kwargs)

                    # Record success call
                    self.metrics_service.increment_counter(
                        "function_calls_total",
                        1.0,
                        {**(labels or {}), "function": name, "status": "success"},
                    )

                    return result

                except Exception as e:
                    # Record error call
                    self.metrics_service.increment_counter(
                        "function_calls_total",
                        1.0,
                        {**(labels or {}), "function": name, "status": "error"},
                    )

                    self.metrics_service.record_error(
                        error_type=type(e).__name__,
                        component=name,
                    )

                    raise

            return wrapper

        return decorator

    def track_errors(
        self: MetricsDecorators,
        function_name: str | None = None,
        labels: dict[str, str] | None = None,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """Decorator to track function errors.

        Args:
        ----
            function_name: Custom function name for metrics.
            labels: Additional labels for metrics.

        Returns:
        -------
            Decorator function.

        """

        def decorator(
            func: Callable[..., T],
        ) -> Callable[[Callable[..., T]], Callable[..., T]]:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                if not self.metrics_service.enabled:
                    return func(*args, **kwargs)

                name = function_name or f"{func.__module__}.{func.__name__}"

                try:
                    return func(*args, **kwargs)

                except Exception as e:
                    # Record error
                    self.metrics_service.record_error(
                        error_type=type(e).__name__,
                        component=name,
                    )

                    self.metrics_service.increment_counter(
                        "function_errors_total",
                        1.0,
                        {
                            **(labels or {}),
                            "function": name,
                            "error_type": type(e).__name__,
                        },
                    )

                    raise

            return wrapper

        return decorator


class MetricsContextManager:
    """Context manager for metrics collection."""

    def __init__(
        self: MetricsContextManager,
        metrics_service: MetricsService,
        operation_name: str,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Initialize metrics context manager.

        Args:
        ----
            metrics_service: The metrics service instance.
            operation_name: Name of the operation being measured.
            labels: Additional labels for metrics.

        Returns:
        -------
            None

        """
        self.metrics_service: MetricsService = metrics_service
        self.operation_name: str = operation_name
        self.labels: dict[str, str] = labels or {}
        self.start_time: float | None = None

    def __enter__(self: MetricsContextManager) -> MetricsContextManager:
        """Enter the context."""
        if self.metrics_service.enabled:
            self.start_time = time.time()

            # Record operation start
            self.metrics_service.increment_counter(
                "operations_started_total",
                1.0,
                {**self.labels, "operation": self.operation_name},
            )

        return self

    def __exit__(
        self: MetricsContextManager,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the context.

        Args:
        ----
            exc_type: Exception type.
            exc_val: Exception value.
            exc_tb: Exception traceback.

        """
        if not self.metrics_service.enabled or self.start_time is None:
            return

        duration: float = time.time() - self.start_time
        status = "error" if exc_type is not None else "success"

        # Record operation completion
        self.metrics_service.observe_histogram(
            "operation_duration_seconds",
            duration,
            {**self.labels, "operation": self.operation_name, "status": status},
        )

        self.metrics_service.increment_counter(
            "operations_completed_total",
            1.0,
            {**self.labels, "operation": self.operation_name, "status": status},
        )

        if exc_type is not None:
            self.metrics_service.record_error(
                error_type=exc_type.__name__,
                component=self.operation_name,
            )
