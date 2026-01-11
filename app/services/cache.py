from __future__ import annotations

import functools
import hashlib
import json
from typing import TYPE_CHECKING, Any

from app.services.base_service import BaseService

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.database.redis import Redis
    from app.services.logger import Logger
    from config import Config


class CacheService(BaseService):
    """Caching service using Redis."""

    def __init__(
        self: CacheService,
        config: Config,
        logger: Logger,
        redis_client: Redis,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize the CacheService.

        Args:
        ----
            config: The configuration to use.
            logger: The logger to use.
            redis_client: The Redis client to use.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        """
        super().__init__(config, logger, *args, **kwargs)
        self.redis_client: Redis = redis_client
        self.default_ttl: int = self.config.get("cache_default_ttl", 300)
        self.prefix: str = self.config.get("cache_prefix", "cache:")
        self.logger.info("CacheService initialized", extra={"service": "CacheService"})

    async def get(self: CacheService, key: str) -> Any:
        """Get a value from cache."""
        full_key = f"{self.prefix}{key}"
        return await self.redis_client.get(full_key)

    async def set(
        self: CacheService, key: str, value: Any, ttl: int | None = None
    ) -> bool:
        """Set a value in cache with TTL."""
        full_key = f"{self.prefix}{key}"
        return await self.redis_client.set(
            full_key, value, expire=ttl or self.default_ttl
        )

    async def delete(self: CacheService, key: str) -> int:
        """Delete a value from cache."""
        full_key = f"{self.prefix}{key}"
        return await self.redis_client.delete(full_key)

    async def clear_pattern(self: CacheService, pattern: str) -> int:
        """Clear all keys matching a pattern.

        Args:
        ----
            pattern: The pattern to match.

        Returns:
        -------
            The number of keys deleted.

        """
        return await self.redis_client.delete_pattern(pattern)

    def cached(self: CacheService, ttl: int | None = None) -> Callable:
        """Decorator for caching function results."""

        def decorator(func: Callable) -> Callable:
            """Decorator for caching function results."""

            @functools.wraps(func)
            async def wrapper(*args: dict[str, Any], **kwargs: dict[str, Any]) -> Any:
                """Wrapper for caching function results."""
                # Generate a cache key based on function name and arguments
                key_parts = [func.__module__, func.__name__]

                # Add args and kwargs to key
                if args:
                    key_parts.append(str(args))
                if kwargs:
                    key_parts.append(str(sorted(kwargs.items())))

                cache_key = hashlib.md5(json.dumps(key_parts).encode()).hexdigest()

                # Try to get from cache
                cached_result = await self.get(cache_key)
                if cached_result is not None:
                    self.logger.debug(f"Cache hit for {func.__name__}")
                    return cached_result

                # Cache miss, execute function
                self.logger.debug(f"Cache miss for {func.__name__}")

                result = await func(*args, **kwargs)

                # Store in cache
                await self.set(cache_key, result, ttl)

                return result

            return wrapper

        return decorator

    async def connect(self: CacheService) -> None:
        """Connect to the Redis backend if needed."""
        if not hasattr(self.redis_client, "connect"):
            return

        try:
            await self.redis_client.connect()
            self.logger.info("CacheService connected to Redis.")
        except Exception as e:
            self.logger.error(f"CacheService failed to connect: {e}")
            raise

    async def close(self: CacheService) -> None:
        """Close the Redis backend connection if needed."""
        if not hasattr(self.redis_client, "close"):
            return

        try:
            await self.redis_client.close()
            self.logger.info("CacheService closed Redis connection.")
        except Exception as e:
            self.logger.error(f"CacheService failed to close: {e}")
            raise
