"""Retry service with exponential backoff and jitter, fully configurable."""

from __future__ import annotations

import asyncio
import random
import time
from functools import wraps
from typing import TYPE_CHECKING, Any

from app.services.base_service import BaseService
from app.services.error.exceptions import RetryExhaustedError

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.services.logger import Logger
    from config import Config


class RetryService(BaseService):
    """Service for retries with exponential backoff and optional jitter."""

    def __init__(
        self: RetryService,
        logger: Logger,
        config: Config,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize the RetryService.

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

        # Configurable defaults
        self.default_max_retries: int = config.get("retry_max_attempts", 3)
        self.default_base_delay: float = config.get("retry_base_delay", 1.0)
        self.default_max_delay: float = config.get("retry_max_delay", 60.0)
        self.default_exponential_base: float = config.get("retry_exponential_base", 2.0)
        self.default_jitter: bool = config.get("retry_jitter", True)

        # Strategy overrides (per operation type)
        self.strategies: dict[str, dict[str, float | int]] = config.get(
            "retry_strategies",
            {
                "database": {"max_retries": 5, "base_delay": 0.5, "max_delay": 10.0},
                "http": {"max_retries": 3, "base_delay": 1.0, "max_delay": 30.0},
                "cache": {"max_retries": 2, "base_delay": 0.1, "max_delay": 1.0},
                "auth": {"max_retries": 2, "base_delay": 0.5, "max_delay": 5.0},
            },
        )

        # Retryable exceptions
        self.retryable_exceptions: set[type[Exception]] = set(
            config.get(
                "retryable_exceptions",
                {ConnectionError, TimeoutError, asyncio.TimeoutError},
            )
        )

        # Metrics
        self.total_retries: int = 0
        self.successful_retries: int = 0
        self.failed_retries: int = 0

        self.logger.info("Retry Service Initialized", extra={"service": "RetryService"})

    def add_retryable_exception(self: RetryService, exc_type: type[Exception]) -> None:
        """Add a retryable exception.

        Args:
        ----
            exc_type: The type of exception to add.

        Returns:
        -------
            None

        """
        self.retryable_exceptions.add(exc_type)

    def remove_retryable_exception(
        self: RetryService, exc_type: type[Exception]
    ) -> None:
        """Remove a retryable exception.

        Args:
        ----
            exc_type: The type of exception to remove.

        Returns:
        -------
            None

        """
        self.retryable_exceptions.discard(exc_type)

    def _calculate_delay(
        self: RetryService, attempt: int, base: float, max_delay: float, exp_base: float
    ) -> float:
        """Compute exponential backoff with optional jitter.

        Args:
        ----
            attempt: The attempt number.
            base: The base delay.
            max_delay: The maximum delay.
            exp_base: The exponential base.

        Returns:
        -------
            The calculated delay.

        """
        delay = min(base * (exp_base**attempt), max_delay)
        if self.default_jitter:
            jitter = delay * 0.1
            delay += random.uniform(-jitter, jitter)
        return max(0, delay)

    def _should_retry(
        self: RetryService, exc: Exception, custom_exceptions: set[type] | None = None
    ) -> bool:
        """Check if exception is retryable.

        Args:
        ----
            exc: The exception to check.
            custom_exceptions: The custom exceptions to check.

        Returns:
        -------
            True if the exception is retryable, False otherwise.

        """
        exceptions = custom_exceptions or self.retryable_exceptions
        return any(isinstance(exc, e) for e in exceptions)

    async def retry_async(
        self: RetryService,
        func: Callable[..., Any],
        *args: dict[str, Any],
        strategy: str | None = None,
        max_retries: int | None = None,
        base_delay: float | None = None,
        max_delay: float | None = None,
        exponential_base: float | None = None,
        retryable_exceptions: set[type[Exception]] | None = None,
        on_retry: Callable[[int, Exception], None] | None = None,
        **kwargs: dict[str, Any],
    ) -> Any:
        """Retry an async function with exponential backoff.

        Args:
        ----
            func: The function to retry.
            *args: The arguments to pass to the function.
            strategy: The strategy to use.
            max_retries: The maximum number of retries.
            base_delay: The base delay.
            max_delay: The maximum delay.
            exponential_base: The exponential base.
            retryable_exceptions: The retryable exceptions.
            on_retry: The function to call on retry.
            **kwargs: The keyword arguments to pass to the function.

        Returns:
        -------
            The result of the function.

        """
        cfg = self.strategies.get(strategy, {})
        max_retries = (
            max_retries
            if max_retries is not None
            else cfg.get("max_retries", self.default_max_retries)
        )
        base_delay = (
            base_delay
            if base_delay is not None
            else cfg.get("base_delay", self.default_base_delay)
        )
        max_delay = (
            max_delay
            if max_delay is not None
            else cfg.get("max_delay", self.default_max_delay)
        )
        exponential_base = exponential_base or self.default_exponential_base

        last_exc: Exception | None = None
        start_time = time.time()

        for attempt in range(max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                if attempt > 0:
                    self.successful_retries += 1
                    elapsed = time.time() - start_time
                    self.logger.info(
                        f"Retry successful after {attempt} attempts",
                        extra={
                            "attempts": attempt,
                            "elapsed": elapsed,
                            "strategy": strategy,
                        },
                    )
                return result
            except Exception as exc:
                last_exc = exc
                if not self._should_retry(exc, retryable_exceptions):
                    raise
                if attempt >= max_retries:
                    self.failed_retries += 1
                    elapsed = time.time() - start_time
                    self.logger.error(
                        f"Retry exhausted after {max_retries} attempts",
                        extra={
                            "attempts": max_retries,
                            "elapsed": elapsed,
                            "error": str(exc),
                            "strategy": strategy,
                        },
                    )
                    raise RetryExhaustedError(
                        f"Failed after {max_retries} retries", last_exc
                    )

                delay = self._calculate_delay(
                    attempt, base_delay, max_delay, exponential_base
                )
                self.total_retries += 1
                self.logger.warning(
                    f"Retrying {func.__name__} in {delay:.2f}s (attempt {attempt + 1}/{max_retries})",
                    extra={
                        "attempt": attempt + 1,
                        "max_attempts": max_retries,
                        "delay": delay,
                        "error": str(exc),
                    },
                )
                if on_retry:
                    on_retry(attempt + 1, exc)
                await asyncio.sleep(delay)

        raise RetryExhaustedError("Unexpected retry exhaustion", last_exc)

    def retry_sync(
        self: RetryService,
        func: Callable[..., Any],
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> Any:
        """Synchronous retry wrapper.

        Args:
        ----
            func: The function to retry.
            *args: The arguments to pass to the function.
            **kwargs: The keyword arguments to pass to the function.

        Returns:
        -------
            The result of the function.

        """
        # Use async logic via an event loop if called in sync context
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.retry_async(func, *args, **kwargs))

    def with_retry(
        self: RetryService,
        strategy: str | None = None,
        max_retries: int | None = None,
        base_delay: float | None = None,
        max_delay: float | None = None,
        exponential_base: float | None = None,
        retryable_exceptions: set[type[Exception]] | None = None,
    ) -> Callable:
        """Decorator for adding retry logic.

        Args:
        ----
            strategy: The strategy to use.
            max_retries: The maximum number of retries.
            base_delay: The base delay.
            max_delay: The maximum delay.
            exponential_base: The exponential base.
            retryable_exceptions: The retryable exceptions.

        Returns:
        -------
            The decorator.

        """

        def decorator(func: Callable) -> Callable:
            """Decorator for adding retry logic.

            Args:
            ----
                func: The function to retry.

            Returns:
            -------
                The decorator.

            """
            if asyncio.iscoroutinefunction(func):

                @wraps(func)
                async def async_wrapper(
                    *args: dict[str, Any], **kwargs: dict[str, Any]
                ) -> Any:
                    """Async wrapper for adding retry logic.

                    Args:
                    ----
                        *args: The arguments to pass to the function.
                        **kwargs: The keyword arguments to pass to the function.

                    Returns:
                    -------
                        The result of the function.

                    """
                    return await self.retry_async(
                        func,
                        *args,
                        strategy=strategy,
                        max_retries=max_retries,
                        base_delay=base_delay,
                        max_delay=max_delay,
                        exponential_base=exponential_base,
                        retryable_exceptions=retryable_exceptions,
                        **kwargs,
                    )

                return async_wrapper
            else:

                @wraps(func)
                def sync_wrapper(
                    *args: dict[str, Any], **kwargs: dict[str, Any]
                ) -> Any:
                    """Sync wrapper for adding retry logic.

                    Args:
                    ----
                        *args: The arguments to pass to the function.
                        **kwargs: The keyword arguments to pass to the function.

                    Returns:
                    -------
                        The result of the function.

                    """
                    return self.retry_sync(
                        func,
                        *args,
                        strategy=strategy,
                        max_retries=max_retries,
                        base_delay=base_delay,
                        max_delay=max_delay,
                        exponential_base=exponential_base,
                        retryable_exceptions=retryable_exceptions,
                        **kwargs,
                    )

                return sync_wrapper

        return decorator

    def get_metrics(self: RetryService) -> dict[str, int | float]:
        """Return retry metrics.

        Returns
        -------
            The retry metrics.

        """
        success_rate = (
            self.successful_retries / self.total_retries if self.total_retries else 0
        )
        return {
            "total_retries": self.total_retries,
            "successful_retries": self.successful_retries,
            "failed_retries": self.failed_retries,
            "success_rate": success_rate,
        }
