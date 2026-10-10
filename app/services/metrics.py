"""Prometheus metrics for HTTP traffic.

Uses a private registry (a module-global one makes a second application instance in the
same process fail with duplicate series) and bounded labels: the endpoint label is the
matched route template, never the raw URL.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest
from prometheus_client.process_collector import ProcessCollector

from app.services.base_service import BaseService

if TYPE_CHECKING:
    from app.services.logger import Logger
    from config import Config

LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


class MetricsService(BaseService):
    """Request counters and latency histograms, rendered in Prometheus text format."""

    def __init__(self, logger: Logger, config: Config) -> None:
        super().__init__(config, logger)
        self.registry = CollectorRegistry()
        ProcessCollector(registry=self.registry)
        self.requests = Counter(
            "http_requests_total",
            "HTTP requests by route template and status",
            ["method", "endpoint", "status"],
            registry=self.registry,
        )
        self.latency = Histogram(
            "http_request_duration_seconds",
            "HTTP request latency",
            ["method", "endpoint"],
            buckets=LATENCY_BUCKETS,
            registry=self.registry,
        )

    def track_request(self, method: str, endpoint: str, status_code: int, duration: float) -> None:
        """Record one finished request. ``endpoint`` must be a route template."""
        self.requests.labels(method, endpoint, str(status_code)).inc()
        self.latency.labels(method, endpoint).observe(duration)

    def render(self) -> bytes:
        """The registry in Prometheus text exposition format."""
        return generate_latest(self.registry)


__all__ = ["MetricsService"]
