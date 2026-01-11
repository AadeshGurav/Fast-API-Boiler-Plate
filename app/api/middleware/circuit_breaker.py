"""Circuit breaker pattern implementation with extensive logging.

The circuit breaker prevents cascading failures by monitoring service health
and temporarily blocking calls to failing services.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from enum import Enum
from typing import Any

from fastapi import HTTPException, Request, Response
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE

from app.api.middleware.base import BaseMiddleware
from app.services.logger import Logger


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking calls due to failures
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker for a specific service or endpoint with detailed logging."""

    def __init__(
        self: CircuitBreaker,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: float = 60.0,
        half_open_requests: int = 3,
        logger: Logger | None = None,
    ) -> None:
        """Initialize the CircuitBreaker.

        Args:
        ----
            name: The name of the circuit breaker.
            failure_threshold: The number of failures before opening the circuit.
            success_threshold: The number of successes in half-open before closing the circuit.
            timeout: The time in seconds before attempting to close the circuit.
            half_open_requests: The number of requests allowed in half-open state.
            logger: The logger instance.
            config: The configuration instance.

        """
        self.name = name
        self.logger = logger
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.half_open_requests = half_open_requests

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_count = 0
        self.last_failure_time: float | None = None

        # Metrics
        self.total_requests = 0
        self.total_failures = 0
        self.total_successes = 0
        self.circuit_opens = 0

        self.logger.info(
            f"CircuitBreaker '{self.name}' initialized",
            extra={
                "state": self.state.value,
                "service": "CircuitBreaker",
                "middleware": "CircuitBreaker",
            },
        )

    def _should_attempt_reset(self: CircuitBreaker) -> bool:
        """Check if the circuit breaker should attempt to reset.

        Returns
        -------
            True if the circuit breaker should attempt to reset, False otherwise.

        """
        should_reset = (
            self.state == CircuitState.OPEN
            and self.last_failure_time is not None
            and time.time() - self.last_failure_time >= self.timeout
        )
        self.logger.debug(
            f"Checking reset for '{self.name}': {should_reset}",
            extra={
                "state": self.state.value,
                "last_failure_time": self.last_failure_time,
                "middleware": "CircuitBreaker",
            },
        )
        return should_reset

    def _trip_breaker(self: CircuitBreaker) -> None:
        """Trip the circuit breaker to the OPEN state."""
        self.state = CircuitState.OPEN
        self.circuit_opens += 1
        self.last_failure_time = time.time()
        self.logger.warning(
            f"Circuit '{self.name}' tripped to OPEN",
            extra={
                "failure_count": self.failure_count,
                "total_failures": self.total_failures,
                "service": "CircuitBreaker",
                "middleware": "CircuitBreaker",
            },
        )

    def _reset(self: CircuitBreaker) -> None:
        """Reset the circuit breaker to the CLOSED state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_count = 0
        self.logger.info(
            f"Circuit '{self.name}' reset to CLOSED",
            extra={"service": "CircuitBreaker", "middleware": "CircuitBreaker"},
        )

    def _half_open(self: CircuitBreaker) -> None:
        """Move the circuit breaker to the HALF_OPEN state."""
        self.state = CircuitState.HALF_OPEN
        self.half_open_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.logger.info(
            f"Circuit '{self.name}' moved to HALF_OPEN",
            extra={"service": "CircuitBreaker", "middleware": "CircuitBreaker"},
        )

    async def call(self: CircuitBreaker, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker.

        Args:
        ----
            func: The function to execute.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
        -------
            The result of the function.

        """
        self.total_requests += 1
        self.logger.debug(
            f"Executing call through circuit '{self.name}'",
            extra={
                "state": self.state.value,
                "total_requests": self.total_requests,
                "middleware": "CircuitBreaker",
            },
        )

        if self._should_attempt_reset():
            self._half_open()

        if self.state == CircuitState.OPEN:
            self.logger.error(
                f"Circuit '{self.name}' is OPEN, blocking request",
                extra={"service": "CircuitBreaker", "middleware": "CircuitBreaker"},
            )
            raise HTTPException(
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service {self.name} temporarily unavailable (circuit open)",
            )

        if self.state == CircuitState.HALF_OPEN:
            self.half_open_count += 1
            self.logger.debug(
                f"Circuit '{self.name}' HALF_OPEN attempt {self.half_open_count}/{self.half_open_requests}",
                extra={"service": "CircuitBreaker", "middleware": "CircuitBreaker"},
            )
            if self.half_open_count > self.half_open_requests:
                self._trip_breaker()
                raise HTTPException(
                    status_code=HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Service {self.name} still recovering (half-open limit reached)",
                )

        try:
            result = (
                await func(*args, **kwargs)
                if asyncio.iscoroutinefunction(func)
                else func(*args, **kwargs)
            )
            self.on_success()
            return result
        except Exception as e:
            self.logger.error(
                f"Circuit '{self.name}' call failed: {e}",
                extra={
                    "state": self.state.value,
                    "service": "CircuitBreaker",
                    "middleware": "CircuitBreaker",
                },
            )
            self.on_failure()
            raise

    def on_success(self: CircuitBreaker) -> None:
        """Record a success."""
        self.total_successes += 1
        self.logger.debug(
            f"Circuit '{self.name}' recorded success",
            extra={
                "state": self.state.value,
                "total_successes": self.total_successes,
                "middleware": "CircuitBreaker",
            },
        )

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._reset()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def on_failure(self: CircuitBreaker) -> None:
        """Record a failure."""
        self.total_failures += 1
        self.last_failure_time = time.time()
        self.logger.debug(
            f"Circuit '{self.name}' recorded failure",
            extra={
                "state": self.state.value,
                "total_failures": self.total_failures,
                "middleware": "CircuitBreaker",
            },
        )

        if self.state == CircuitState.HALF_OPEN:
            self._trip_breaker()
        elif self.state == CircuitState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self._trip_breaker()

    def get_state(self: CircuitBreaker) -> dict[str, Any]:
        """Return current state and metrics.

        Returns
        -------
            The current state and metrics.

        """
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "circuit_opens": self.circuit_opens,
            "last_failure_time": self.last_failure_time,
        }


class CircuitBreakerMiddleware(BaseMiddleware):
    """Middleware to apply circuit breaker to API routes with full logging."""

    def initialize(
        self: CircuitBreakerMiddleware,
        **kwargs,
    ) -> None:
        """Initialize the CircuitBreakerMiddleware.

        Args:
        ----
            failure_threshold: The number of failures before opening the circuit.
            success_threshold: The number of successes in half-open before closing the circuit.
            timeout: The time in seconds before attempting to close the circuit.
            half_open_requests: The number of requests allowed in half-open state.
            monitored_routes: The routes to monitor.
            logger: The logger instance.
            config: The configuration instance.
            kwargs: Additional keyword arguments.

        """
        self.failure_threshold = self.config.get("circuit_breaker_failure_threshold", 5)
        self.success_threshold = self.config.get("circuit_breaker_success_threshold", 2)
        self.timeout = self.config.get("circuit_breaker_timeout", 60.0)
        self.half_open_requests = self.config.get(
            "circuit_breaker_half_open_requests", 3
        )
        self.monitored_routes = self.config.get("circuit_breaker_monitored_routes", {})
        self.circuit_breakers: dict[str, CircuitBreaker] = {}

        self.logger.info(
            "CircuitBreakerMiddleware initialized",
            extra={
                "middleware": "CircuitBreakerMiddleware",
                "routes_monitored": list(self.monitored_routes.keys()),
            },
        )

    def _get_circuit_breaker(
        self: CircuitBreakerMiddleware, path: str
    ) -> CircuitBreaker | None:
        """Get the circuit breaker for the path.

        Args:
        ----
            path: The path to get the circuit breaker for.

        Returns:
        -------
            The circuit breaker for the path.

        """
        should_monitor = not self.monitored_routes
        settings = {
            "failure_threshold": self.failure_threshold,
            "success_threshold": self.success_threshold,
            "timeout": self.timeout,
            "half_open_requests": self.half_open_requests,
            "logger": self.logger,
        }

        for pattern, route_settings in self.monitored_routes.items():
            if pattern in path or path.startswith(pattern):
                should_monitor = True
                settings.update(route_settings)
                break

        if not should_monitor:
            self.logger.debug(f"Path '{path}' not monitored by circuit breaker")
            return None

        if path not in self.circuit_breakers:
            self.circuit_breakers[path] = CircuitBreaker(name=path, **settings)
            self.logger.info(f"Circuit breaker created for path '{path}'")

        return self.circuit_breakers[path]

    async def process_request(
        self: CircuitBreakerMiddleware, request: Request, call_next: Callable
    ) -> Response:
        """Process the request through the circuit breaker.

        Args:
        ----
            request: The request object.
            call_next: The next function to call.

        Returns:
        -------
            The response object.

        """
        path = request.url.path
        circuit_breaker = self._get_circuit_breaker(path)

        if not circuit_breaker:
            self.logger.debug(f"No circuit breaker for path '{path}', passing request")
            return await call_next(request)

        try:
            response = await circuit_breaker.call(call_next, request)
            if response.status_code >= 500:
                circuit_breaker.on_failure()
            else:
                circuit_breaker.on_success()

            response.headers["X-Circuit-Breaker-State"] = circuit_breaker.state.value
            self.logger.debug(
                f"Request processed through circuit '{circuit_breaker.name}'",
                extra={
                    "state": circuit_breaker.state.value,
                    "middleware": "CircuitBreaker",
                },
            )
            return response
        except HTTPException:
            self.logger.warning(
                f"Request blocked by circuit '{circuit_breaker.name}'",
                extra={
                    "state": circuit_breaker.state.value,
                    "middleware": "CircuitBreaker",
                },
            )
            raise
        except Exception as e:
            self.logger.error(
                f"Unhandled exception in circuit '{circuit_breaker.name}': {e}",
                extra={
                    "state": circuit_breaker.state.value,
                    "middleware": "CircuitBreaker",
                },
            )
            circuit_breaker.on_failure()
            raise

    def get_all_states(self: CircuitBreakerMiddleware) -> dict[str, dict[str, Any]]:
        """Get the state of all circuit breakers.

        Returns
        -------
            The state of all circuit breakers.

        """
        return {path: cb.get_state() for path, cb in self.circuit_breakers.items()}

    def reset_circuit_breaker(self: CircuitBreakerMiddleware, path: str) -> bool:
        """Reset the circuit breaker for the path.

        Args:
        ----
            path: The path to reset the circuit breaker for.

        Returns:
        -------
            True if the circuit breaker was reset, False otherwise.

        """
        if path in self.circuit_breakers:
            self.circuit_breakers[path]._reset()
            self.logger.info(
                f"Circuit breaker '{path}' manually reset",
                extra={"middleware": "CircuitBreaker"},
            )
            return True
        return False

    def reset_all_circuit_breakers(self: CircuitBreakerMiddleware) -> None:
        """Reset all circuit breakers."""
        for cb in self.circuit_breakers.values():
            cb._reset()
            self.logger.info(
                f"Circuit breaker '{cb.name}' manually reset",
                extra={"middleware": "CircuitBreaker"},
            )
