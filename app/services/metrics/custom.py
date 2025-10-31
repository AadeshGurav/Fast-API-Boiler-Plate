"""Custom metrics functionality for business logic."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from prometheus_client import Counter, Gauge, Histogram

if TYPE_CHECKING:
    from app.services.logger import Logger


class CustomMetricsMixin:
    """Mixin for custom business metrics functionality."""

    def __init__(self: CustomMetricsMixin, logger: Logger, registry: Any) -> None:
        """Initialize custom metrics mixin.

        Args:
        ----
            logger: The logger to use.
            registry: Prometheus registry.

        """
        self.logger: Logger = logger
        self.registry: Any = registry
        self.custom_counters: dict[str, Counter] = {}
        self.custom_gauges: dict[str, Gauge] = {}
        self.custom_histograms: dict[str, Histogram] = {}

    def create_counter(
        self: CustomMetricsMixin,
        name: str,
        description: str,
        labels: list[str] | None = None,
    ) -> Counter:
        """Create a custom counter metric.

        Args:
        ----
            name: Metric name.
            description: Metric description.
            labels: Optional list of label names.

        Returns:
        -------
            Created Counter metric.

        """
        if name in self.custom_counters:
            return self.custom_counters[name]

        labels: list[str] = labels or []
        counter: Counter = Counter(
            name,
            description,
            labels,
            registry=self.registry,
        )

        self.custom_counters[name] = counter

        self.logger.info(
            "Custom counter created",
            extra={
                "service": "CustomMetricsMixin",
                "name": name,
                "description": description,
                "labels": labels,
            },
        )

        return counter

    def create_gauge(
        self: CustomMetricsMixin,
        name: str,
        description: str,
        labels: list[str] | None = None,
    ) -> Gauge:
        """Create a custom gauge metric.

        Args:
        ----
            name: Metric name.
            description: Metric description.
            labels: Optional list of label names.

        Returns:
        -------
            Created Gauge metric.

        """
        if name in self.custom_gauges:
            return self.custom_gauges[name]

        labels: list[str] = labels or []
        gauge: Gauge = Gauge(
            name,
            description,
            labels,
            registry=self.registry,
        )

        self.custom_gauges[name] = gauge

        self.logger.info(
            "Custom gauge created",
            extra={
                "service": "CustomMetricsMixin",
                "name": name,
                "description": description,
                "labels": labels,
            },
        )

        return gauge

    def create_histogram(
        self: CustomMetricsMixin,
        name: str,
        description: str,
        labels: list[str] | None = None,
        buckets: list[float] | None = None,
    ) -> Histogram:
        """Create a custom histogram metric.

        Args:
        ----
            name: Metric name.
            description: Metric description.
            labels: Optional list of label names.
            buckets: Optional custom buckets.

        Returns:
        -------
            Created Histogram metric.

        """
        if name in self.custom_histograms:
            return self.custom_histograms[name]

        labels: list[str] = labels or []
        histogram: Histogram = Histogram(
            name,
            description,
            labels,
            buckets=buckets,
            registry=self.registry,
        )

        self.custom_histograms[name] = histogram

        self.logger.info(
            "Custom histogram created",
            extra={
                "service": "CustomMetricsMixin",
                "name": name,
                "description": description,
                "labels": labels,
                "buckets": buckets,
            },
        )

        return histogram

    def increment_counter(
        self: CustomMetricsMixin,
        name: str,
        value: float = 1.0,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Increment a custom counter.

        Args:
        ----
            name: Counter name.
            value: Value to increment by.
            labels: Optional label values.

        """
        if name not in self.custom_counters:
            self.logger.warning(
                "Counter not found",
                extra={"service": "CustomMetricsMixin", "name": name},
            )
            return

        labels: dict[str, str] = labels or {}
        self.custom_counters[name].labels(**labels).inc(value)

        self.logger.debug(
            "Counter incremented",
            extra={
                "service": "CustomMetricsMixin",
                "name": name,
                "value": value,
                "labels": labels,
            },
        )

    def set_gauge(
        self: CustomMetricsMixin,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Set a custom gauge value.

        Args:
        ----
            name: Gauge name.
            value: Value to set.
            labels: Optional label values.

        """
        if name not in self.custom_gauges:
            self.logger.warning(
                "Gauge not found",
                extra={"service": "CustomMetricsMixin", "name": name},
            )
            return

        labels: dict[str, str] = labels or {}
        self.custom_gauges[name].labels(**labels).set(value)

        self.logger.debug(
            "Gauge set",
            extra={
                "service": "CustomMetricsMixin",
                "name": name,
                "value": value,
                "labels": labels,
            },
        )

    def observe_histogram(
        self: CustomMetricsMixin,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Observe a histogram value.

        Args:
        ----
            name: Histogram name.
            value: Value to observe.
            labels: Optional label values.

        """
        if name not in self.custom_histograms:
            self.logger.warning(
                "Histogram not found",
                extra={"service": "CustomMetricsMixin", "name": name},
            )
            return

        labels: dict[str, str] = labels or {}
        self.custom_histograms[name].labels(**labels).observe(value)

        self.logger.debug(
            "Histogram observed",
            extra={
                "service": "CustomMetricsMixin",
                "name": name,
                "value": value,
                "labels": labels,
            },
        )

    def get_custom_metrics(self: CustomMetricsMixin) -> dict[str, Any]:
        """Get all custom metrics.

        Returns
        -------
            Dictionary of custom metrics.

        """
        return {
            "counters": list(self.custom_counters.keys()),
            "gauges": list(self.custom_gauges.keys()),
            "histograms": list(self.custom_histograms.keys()),
        }
