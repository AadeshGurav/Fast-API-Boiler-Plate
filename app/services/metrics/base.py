"""Base metrics service with core functionality."""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING

from prometheus_client import REGISTRY, Counter, Gauge, Histogram, Info, generate_latest

if TYPE_CHECKING:
    from types import TracebackType

    from app.services.logger import Logger
    from config import Config


class ActiveRequestContext:
    """Context manager for tracking active requests."""

    def __init__(
        self: ActiveRequestContext,
        metrics_service: MetricsService,
        method: str,
        endpoint: str,
    ) -> None:
        """Initialize active request context.

        Args:
        ----
            metrics_service: The metrics service instance.
            method: HTTP method.
            endpoint: HTTP endpoint.

        """
        self.metrics_service: MetricsService = metrics_service
        self.method: str = method
        self.endpoint: str = endpoint
        self.start_time: float | None = None

    def __enter__(self: ActiveRequestContext) -> ActiveRequestContext:
        """Enter the context.

        Returns
        -------
            ActiveRequestContext.

        """
        if self.metrics_service.enabled:
            self.start_time = time.time()
            # Could add active request counter here if needed
        return self

    def __exit__(
        self: ActiveRequestContext,
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

        duration = time.time() - self.start_time
        status_code = 500 if exc_type is not None else 200

        # Track the request using the enhanced track_request method
        self.metrics_service.track_request(
            method=self.method,
            endpoint=self.endpoint,
            status_code=status_code,
            duration=duration,
        )


class MetricsService:
    """Service for collecting and exposing application metrics.

    Features:
        - Request metrics (rate, latency, errors)
        - Resource metrics (connections, memory, CPU)
        - Business metrics (custom counters, gauges, histograms)
        - Integration with Prometheus
        - Full structured logging for all actions
    """

    def __init__(self: MetricsService, logger: Logger, config: dict) -> None:
        """Initialize the MetricsService.

        Args:
        ----
            logger: The logger to use.
            config: The configuration to use.

        Returns:
        -------
            None

        """
        self.enabled: bool = config.get("metrics_enabled", True)

        if not self.enabled:
            self.logger.info(
                "Metrics collection disabled", extra={"service": "MetricsService"}
            )
            return

        self.logger: Logger = logger
        self.config: Config = config

        # Use custom registry to avoid conflicts
        self.registry = REGISTRY

        # Custom metrics containers
        self.custom_counters: dict[str, Counter] = {}
        self.custom_gauges: dict[str, Gauge] = {}
        self.custom_histograms: dict[str, Histogram] = {}

        # Initialize core metrics
        self._init_core_metrics()

        self.logger.info(
            "MetricsService initialized",
            extra={
                "service": "MetricsService",
                "enabled": self.enabled,
                "registry": str(self.registry),
            },
        )

    def _init_core_metrics(self: MetricsService) -> None:
        """Initialize core application metrics."""
        if not self.enabled:
            return

        # Request metrics
        self.request_counter: Counter = Counter(
            "http_requests_total",
            "Total number of HTTP requests",
            ["method", "endpoint", "status_code"],
            registry=self.registry,
        )

        self.request_duration: Histogram = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint"],
            registry=self.registry,
        )

        # Enhanced request metrics
        self.requests_total: Counter = Counter(
            "requests_total",
            "Total number of HTTP requests",
            ["method", "endpoint", "status"],
            registry=self.registry,
        )

        self.request_size: Histogram = Histogram(
            "request_size_bytes",
            "HTTP request size in bytes",
            ["method", "endpoint"],
            registry=self.registry,
        )

        self.response_size: Histogram = Histogram(
            "response_size_bytes",
            "HTTP response size in bytes",
            ["method", "endpoint"],
            registry=self.registry,
        )

        # Error metrics
        self.error_counter: Counter = Counter(
            "application_errors_total",
            "Total number of application errors",
            ["error_type", "component"],
            registry=self.registry,
        )

        # Resource metrics
        self.active_connections: Gauge = Gauge(
            "active_connections",
            "Number of active connections",
            registry=self.registry,
        )

        self.memory_usage: Gauge = Gauge(
            "memory_usage_bytes",
            "Memory usage in bytes",
            registry=self.registry,
        )

        # Database connection metrics
        self.db_connections_active: Gauge = Gauge(
            "db_connections_active",
            "Number of active database connections",
            ["database"],
            registry=self.registry,
        )

        self.db_connections_idle: Gauge = Gauge(
            "db_connections_idle",
            "Number of idle database connections",
            ["database"],
            registry=self.registry,
        )

        # Cache metrics
        self.cache_hits: Counter = Counter(
            "cache_hits_total",
            "Total number of cache hits",
            ["cache_type", "operation"],
            registry=self.registry,
        )

        self.cache_misses: Counter = Counter(
            "cache_misses_total",
            "Total number of cache misses",
            ["cache_type", "operation"],
            registry=self.registry,
        )

        # Circuit breaker metrics
        self.circuit_breaker_state: Gauge = Gauge(
            "circuit_breaker_state",
            "Circuit breaker state (0=closed, 1=open, 2=half_open)",
            ["service"],
            registry=self.registry,
        )

        self.circuit_breaker_failures: Counter = Counter(
            "circuit_breaker_failures_total",
            "Total number of circuit breaker failures",
            ["service"],
            registry=self.registry,
        )

        # Rate limiting metrics
        self.rate_limit_exceeded: Counter = Counter(
            "rate_limit_exceeded_total",
            "Total number of rate limit violations",
            ["endpoint"],
            registry=self.registry,
        )

        # User metrics
        self.user_logins: Counter = Counter(
            "user_logins_total",
            "Total number of user login attempts",
            ["status"],
            registry=self.registry,
        )

        self.users_total: Gauge = Gauge(
            "users_total",
            "Total number of active users",
            registry=self.registry,
        )

        self.user_sessions_active: Gauge = Gauge(
            "user_sessions_active",
            "Number of active user sessions",
            registry=self.registry,
        )

        # Application info
        self.app_info: Info = Info(
            "application_info",
            "Application information",
            registry=self.registry,
        )

        self.logger.info(
            "Core metrics initialized",
            extra={"service": "MetricsService"},
        )

    def record_request(
        self: MetricsService,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
    ) -> None:
        """Record HTTP request metrics.

        Args:
        ----
            method: HTTP method.
            endpoint: Endpoint path.
            status_code: HTTP status code.
            duration: Request duration in seconds.

        """
        if not self.enabled:
            return

        # Sanitize endpoint for metrics
        sanitized_endpoint: str = self._normalize_endpoint(endpoint)

        self.request_counter.labels(
            method=method,
            endpoint=sanitized_endpoint,
            status_code=str(status_code),
        ).inc()

        self.request_duration.labels(
            method=method, endpoint=sanitized_endpoint
        ).observe(duration)

        self.logger.debug(
            "Request metrics recorded",
            extra={
                "service": "MetricsService",
                "method": method,
                "endpoint": sanitized_endpoint,
                "status_code": status_code,
                "duration": duration,
            },
        )

    def record_error(self: MetricsService, error_type: str, component: str) -> None:
        """Record application error.

        Args:
        ----
            error_type: Type of error.
            component: Component where error occurred.

        """
        if not self.enabled:
            return

        self.error_counter.labels(error_type=error_type, component=component).inc()

        self.logger.debug(
            "Error metrics recorded",
            extra={
                "service": "MetricsService",
                "error_type": error_type,
                "component": component,
            },
        )

    def update_resource_metrics(
        self: MetricsService, connections: int, memory_bytes: int
    ) -> None:
        """Update resource usage metrics.

        Args:
        ----
            connections: Number of active connections.
            memory_bytes: Memory usage in bytes.

        """
        if not self.enabled:
            return

        self.active_connections.set(connections)
        self.memory_usage.set(memory_bytes)

        self.logger.debug(
            "Resource metrics updated",
            extra={
                "service": "MetricsService",
                "connections": connections,
                "memory_bytes": memory_bytes,
            },
        )

    # --------------------------
    # Tracking methods
    # --------------------------
    def track_request(
        self: MetricsService,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
        request_size: int = 0,
        response_size: int = 0,
    ) -> None:
        """Track HTTP request metrics.

        Args:
        ----
            method: The HTTP method.
            endpoint: The HTTP endpoint.
            status_code: The HTTP status code.
            duration: The HTTP duration.
            request_size: The HTTP request size.
            response_size: The HTTP response size.

        """
        if not self.enabled:
            return

        endpoint: str = self._normalize_endpoint(endpoint)
        self.requests_total.labels(
            method=method, endpoint=endpoint, status=str(status_code)
        ).inc()
        self.request_duration.labels(method=method, endpoint=endpoint).observe(duration)
        if request_size > 0:
            self.request_size.labels(method=method, endpoint=endpoint).observe(
                request_size
            )
        if response_size > 0:
            self.response_size.labels(method=method, endpoint=endpoint).observe(
                response_size
            )

        self.logger.debug(
            "Tracked HTTP request",
            extra={
                "method": method,
                "endpoint": endpoint,
                "status": status_code,
                "duration": duration,
            },
        )

    def track_active_request(
        self: MetricsService, method: str, endpoint: str
    ) -> ActiveRequestContext:
        """Context manager for active requests.

        Args:
        ----
            method: The HTTP method.
            endpoint: The HTTP endpoint.

        Returns:
        -------
            ActiveRequestContext.

        """
        return ActiveRequestContext(self, method, endpoint)

    def track_db_connections(
        self: MetricsService, database: str, active: int, idle: int
    ) -> None:
        """Track database connection metrics.

        Args:
        ----
            database: The database name.
            active: The number of active database connections.
            idle: The number of idle database connections.

        """
        if not self.enabled:
            return

        self.db_connections_active.labels(database=database).set(active)
        self.db_connections_idle.labels(database=database).set(idle)
        self.logger.debug(
            "Tracked DB connections",
            extra={"database": database, "active": active, "idle": idle},
        )

    def track_cache_hit(
        self: MetricsService, cache_type: str = "redis", operation: str = "get"
    ) -> None:
        """Track cache hit metrics.

        Args:
        ----
            cache_type: The cache type.
            operation: The cache operation.

        """
        if not self.enabled:
            return

        self.cache_hits.labels(cache_type=cache_type, operation=operation).inc()
        self.logger.debug(
            "Tracked cache hit",
            extra={"cache_type": cache_type, "operation": operation},
        )

    def track_cache_miss(
        self: MetricsService, cache_type: str = "redis", operation: str = "get"
    ) -> None:
        """Track cache miss metrics.

        Args:
        ----
            cache_type: The cache type.
            operation: The cache operation.

        """
        if not self.enabled:
            return

        self.cache_misses.labels(cache_type=cache_type, operation=operation).inc()
        self.logger.debug(
            "Tracked cache miss",
            extra={"cache_type": cache_type, "operation": operation},
        )

    def track_circuit_breaker(
        self: MetricsService, service: str, state: str, failures: int = 0
    ) -> None:
        """Track circuit breaker metrics.

        Args:
        ----
            service: The service name.
            state: The circuit breaker state.
            failures: The number of failures.

        """
        if not self.enabled:
            return

        state_map: dict[str, int] = {"closed": 0, "open": 1, "half_open": 2}
        state_value: int = state_map.get(state, -1)
        self.circuit_breaker_state.labels(service=service).set(state_value)
        if failures > 0:
            self.circuit_breaker_failures.labels(service=service).inc(failures)
        self.logger.debug(
            "Tracked circuit breaker",
            extra={"service": service, "state": state, "failures": failures},
        )

    def track_rate_limit_exceeded(self: MetricsService, endpoint: str) -> None:
        """Track rate limit exceeded metrics.

        Args:
        ----
            endpoint: The endpoint.

        """
        if not self.enabled:
            return

        endpoint: str = self._normalize_endpoint(endpoint)
        self.rate_limit_exceeded.labels(endpoint=endpoint).inc()
        self.logger.debug("Rate limit exceeded", extra={"endpoint": endpoint})

    def track_user_login(self: MetricsService, success: bool) -> None:
        """Track user login metrics.

        Args:
        ----
            success: The login success status.

        """
        if not self.enabled:
            return

        status: str = "success" if success else "failure"
        self.user_logins.labels(status=status).inc()
        self.logger.debug("Tracked user login", extra={"status": status})

    def set_active_users(self: MetricsService, count: int) -> None:
        """Set active users metrics.

        Args:
        ----
            count: The number of active users.

        """
        if not self.enabled:
            return

        self.users_total.set(count)
        self.logger.debug("Set active users", extra={"count": count})

    def set_active_sessions(self: MetricsService, count: int) -> None:
        """Set active sessions metrics.

        Args:
        ----
            count: The number of active sessions.

        """
        if not self.enabled:
            return

        self.user_sessions_active.set(count)
        self.logger.debug("Set active sessions", extra={"count": count})

    def _normalize_endpoint(self: MetricsService, endpoint: str) -> str:
        """Normalize endpoint path for metrics.

        Args:
        ----
            endpoint: Raw endpoint path.

        Returns:
        -------
            Normalized endpoint path.

        """
        # Replace dynamic segments with placeholders
        normalized: str = re.sub(r"/\d+", "/{id}", endpoint)
        normalized: str = re.sub(r"/[a-f0-9-]{36}", "/{uuid}", normalized)
        normalized: str = re.sub(r"/[a-f0-9-]{8,}", "/{hash}", normalized)

        return normalized

    def get_metrics(self: MetricsService) -> str:
        """Get metrics in Prometheus format.

        Returns
        -------
            Metrics in Prometheus format.

        """
        if not self.enabled:
            return ""

        try:
            metrics: bytes = generate_latest(self.registry)
            return metrics.decode("utf-8")
        except Exception as e:  # noqa: BLE001
            self.logger.error(
                "Failed to generate metrics",
                extra={"service": "MetricsService", "error": str(e)},
            )
            return ""

    def __enter__(self: MetricsService) -> MetricsService:
        """Context manager entry.

        Returns
        -------
            MetricsService.

        """
        return self

    def __exit__(
        self: MetricsService,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit.

        Args:
        ----
            exc_type: Exception type.
            exc_val: Exception value.
            exc_tb: Exception traceback.

        """
        if exc_type is not None:
            self.record_error(
                error_type=exc_type.__name__,
                component="MetricsService",
            )
