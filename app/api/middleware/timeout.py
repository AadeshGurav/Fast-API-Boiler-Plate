"""Timeout middleware for request timeout handling and resource isolation.

Implements configurable timeouts and bulkheads for resource protection.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import HTTPException, Request, Response
from starlette.status import HTTP_408_REQUEST_TIMEOUT, HTTP_503_SERVICE_UNAVAILABLE

from app.api.middleware.base import BaseMiddleware
from app.services.logger import Logger


class TimeoutMiddleware(BaseMiddleware):
    """Middleware for handling request timeouts and resource isolation.

    Features:
    - Configurable request timeouts per endpoint
    - Thread pool isolation (bulkheads)
    - Queue management to prevent overload
    - Graceful timeout handling
    """

    def initialize(
        self: TimeoutMiddleware,
        **kwargs,
    ) -> None:
        """Initialize timeout middleware.

        Args:
        ----
            kwargs: Additional keyword arguments.

        """
        self.default_timeout = self.config.get("request_timeout", 1000000.0)
        self.endpoint_timeouts = self.config.get("endpoint_timeouts", {})
        self.enable_bulkheads = self.config.get("enable_bulkheads", True)
        self.queue_size = self.config.get("bulkhead_queue_size", 1000)
        self.max_workers = self.config.get("bulkhead_max_workers", 100)

        # Thread pool for bulkhead pattern
        if self.enable_bulkheads:
            self.executor = ThreadPoolExecutor(
                max_workers=self.max_workers,
                thread_name_prefix="fastapi-worker",
            )
            self.active_tasks = 0
            self.queue = asyncio.Queue(maxsize=self.queue_size)

        # Metrics
        self.timeout_count = 0
        self.queue_full_count = 0
        self.logger.info(
            "TimeoutMiddleware initialized",
            extra={"middleware": "TimeoutMiddleware"},
        )

    def _get_timeout(self: TimeoutMiddleware, path: str) -> float:
        """Get timeout for the given path.

        Args:
        ----
            path: The path to get the timeout for

        Returns:
        -------
            The timeout for the given path

        """
        # Check specific endpoint patterns
        for pattern, timeout in self.endpoint_timeouts.items():
            if pattern in path or path.startswith(pattern):
                self.logger.debug(
                    f"Found timeout for path '{path}', using {timeout} seconds",
                    extra={"middleware": "TimeoutMiddleware"},
                )
                return timeout

        self.logger.debug(
            f"No timeout found for path '{path}', using default timeout",
            extra={"middleware": "TimeoutMiddleware"},
        )
        return self.default_timeout

    async def _handle_with_timeout(
        self: TimeoutMiddleware, request: Request, call_next: Callable, timeout: float
    ) -> Response:
        """Handle request with timeout.

        Args:
        ----
            request: The request to handle
            call_next: The next callable in the middleware chain
            timeout: The timeout for the request

        Returns:
        -------
            The response from the request

        """
        try:
            task = asyncio.create_task(call_next(request))
            response = await asyncio.wait_for(task, timeout=timeout)
            self.logger.debug(
                f"Request completed with timeout {timeout} seconds",
                extra={"middleware": "TimeoutMiddleware"},
            )
            return response

        except asyncio.TimeoutError:
            task.cancel()

            self.timeout_count += 1
            self.logger.warning(
                f"Request timeout: {request.method} {request.url.path}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "timeout_seconds": timeout,
                    "client_ip": request.client.host if request.client else "unknown",
                    "middleware": "TimeoutMiddleware",
                },
            )

            # Return timeout response
            raise HTTPException(
                status_code=HTTP_408_REQUEST_TIMEOUT,
                detail=f"Request timeout after {timeout} seconds",
            )

    async def _handle_with_bulkhead(
        self: TimeoutMiddleware, request: Request, call_next: Callable, timeout: float
    ) -> Response:
        """Handle request with bulkhead isolation.

        Args:
        ----
            request: The request to handle
            call_next: The next callable in the middleware chain
            timeout: The timeout for the request

        Returns:
        -------
            The response from the request

        """
        # Check if queue is full
        if self.queue.full():
            self.queue_full_count += 1
            self.logger.warning(
                f"Request queue full: {request.method} {request.url.path}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "queue_size": self.queue_size,
                    "active_tasks": self.active_tasks,
                    "middleware": "TimeoutMiddleware",
                },
            )

            raise HTTPException(
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
                detail="Server overloaded, please try again later",
            )

        # Add to queue
        queue_entry = {
            "request": request,
            "call_next": call_next,
            "timeout": timeout,
            "timestamp": time.time(),
        }

        try:
            await self.queue.put(queue_entry)
            entry = await self.queue.get()
            queue_time = time.time() - entry["timestamp"]

            if queue_time > entry["timeout"]:
                raise HTTPException(
                    status_code=HTTP_408_REQUEST_TIMEOUT,
                    detail=f"Request timed out in queue after {queue_time:.2f} seconds",
                )

            remaining_timeout = entry["timeout"] - queue_time

            return await self._handle_with_timeout(
                entry["request"], entry["call_next"], remaining_timeout
            )

        finally:
            self.queue.task_done()

    async def process_request(
        self: TimeoutMiddleware, request: Request, call_next: Callable
    ) -> Response:
        """Process request with timeout and optional bulkhead.

        Args:
        ----
            request: The request to process
            call_next: The next callable in the middleware chain

        Returns:
        -------
            The response from the request

        """
        timeout = self._get_timeout(request.url.path)

        request.state.timeout = timeout

        if self.enable_bulkheads:
            response = await self._handle_with_bulkhead(request, call_next, timeout)
        else:
            response = await self._handle_with_timeout(request, call_next, timeout)

        response.headers["X-Timeout"] = str(timeout)

        return response

    def get_stats(self: TimeoutMiddleware) -> dict[str, Any]:
        """Get middleware statistics.

        Returns
        -------
            The statistics of the middleware

        """
        stats = {
            "timeout_count": self.timeout_count,
            "queue_full_count": self.queue_full_count,
            "default_timeout": self.default_timeout,
        }

        if self.enable_bulkheads:
            stats.update(
                {
                    "queue_size": self.queue.qsize() if hasattr(self, "queue") else 0,
                    "max_queue_size": self.queue_size,
                    "active_tasks": self.active_tasks,
                }
            )

        return stats

    async def shutdown(self: TimeoutMiddleware) -> None:
        """Gracefully shutdown the middleware."""
        if self.enable_bulkheads and hasattr(self, "executor"):
            if hasattr(self, "queue"):
                await self.queue.join()

            self.executor.shutdown(wait=True)


class BulkheadManager:
    """Manager for creating isolated resource pools (bulkheads).

    Provides thread pool isolation for different types of operations
    to prevent cascading failures.
    """

    def __init__(self: BulkheadManager, logger: Logger) -> None:
        """Initialize the BulkheadManager.

        Args:
        ----
            logger: The logger instance.

        """
        self.logger = logger
        self.bulkheads: dict[str, ThreadPoolExecutor] = {}

    def create_bulkhead(
        self: BulkheadManager, name: str, max_workers: int = 10
    ) -> ThreadPoolExecutor:
        """Create a new bulkhead (isolated thread pool).

        Args:
        ----
            name: The name of the bulkhead
            max_workers: The maximum number of workers in the bulkhead

        Returns:
        -------
            The created bulkhead

        """
        if name not in self.bulkheads:
            self.bulkheads[name] = ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix=f"bulkhead-{name}",
            )

            self.logger.info(f"Created bulkhead '{name}' with {max_workers} workers")

        return self.bulkheads[name]

    def get_bulkhead(self: BulkheadManager, name: str) -> ThreadPoolExecutor | None:
        """Get an existing bulkhead.

        Args:
        ----
            name: The name of the bulkhead

        Returns:
        -------
            The existing bulkhead

        """
        return self.bulkheads.get(name)

    async def execute_in_bulkhead(
        self: BulkheadManager, name: str, func: Callable, *args, **kwargs
    ) -> Any:
        """Execute a function in a specific bulkhead.

        Args:
        ----
            name: The name of the bulkhead
            func: The function to execute
            *args: The arguments to pass to the function
            **kwargs: The keyword arguments to pass to the function

        Returns:
        -------
            The result of the function

        """
        bulkhead = self.get_bulkhead(name)
        if not bulkhead:
            raise ValueError(f"Bulkhead '{name}' does not exist")

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(bulkhead, func, *args, **kwargs)
        self.logger.debug(
            f"Executed function '{func.__name__}' in bulkhead '{name}'",
            extra={"middleware": "TimeoutMiddleware"},
        )
        return result

    def shutdown_all(self: BulkheadManager) -> None:
        """Shutdown all bulkheads."""
        for name, executor in self.bulkheads.items():
            executor.shutdown(wait=True)
            self.logger.info(
                f"Shutdown bulkhead '{name}'", extra={"middleware": "TimeoutMiddleware"}
            )

        self.bulkheads.clear()
