"""Unified data service managing both database and cache backends with logging."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.database.mongodb import MongoDB
from app.database.redis import Redis
from app.services.base_service import BaseService
from app.services.cache import CacheService
from app.services.database_service import DatabaseService

if TYPE_CHECKING:
    from app.services.logger import Logger
    from config import Config


class DataService(BaseService):
    """Unified data service providing DB and cache management.

    Features:
    - Connect and close lifecycle management
    - Efficient unified data access with cache-first strategy
    - Logging for all operations
    """

    def __init__(
        self: DataService,
        config: Config,
        logger: Logger,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize the DataService.

        Args:
        ----
            config: The configuration to use.
            logger: The logger to use.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
        -------
            None

        """
        super().__init__(config, logger, *args, **kwargs)

        # Initialize database backend (MongoDB by default)
        self.db_backend = MongoDB(
            host=config.get("mongo_host"),
            port=config.get("mongo_port"),
            db_name=config.get("app_database"),
            logger=self.logger,
            config=config,
        )
        self.database_service = DatabaseService(self.db_backend, logger=self.logger)

        # Initialize cache backend (Redis by default)
        self.cache_backend = Redis(
            host=config.get("redis_host"),
            port=config.get("redis_port"),
            db_name=config.get("app_database"),
            password=config.get("redis_password"),
            logger=self.logger,
            config=config,
        )
        self.cache_service = CacheService(self.config, self.logger, self.cache_backend)
        self.logger.info("DataService initialized", extra={"service": "DataService"})

    async def connect(self: DataService) -> None:
        """Connect both database and cache backends."""
        await self.database_service.connect()
        await self.cache_service.connect()

        # Initialize application data after successful connection
        await self.database_service.initialize_application_data(self.config)

        self.logger.info("DataService: All backends connected and initialized.")

    async def close(self: DataService) -> None:
        """Close both database and cache backends."""
        await self.database_service.close()
        await self.cache_service.close()
        self.logger.info("DataService: All backends closed.")

    async def get(
        self: DataService,
        collection: str,
        filters: dict[str, Any],
        cache_key: str | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any] | None:
        """Retrieve a record, optionally using cache first.

        Args:
        ----
            collection: Name of the DB collection.
            filters: Query filters for DB.
            cache_key: Optional cache key to use.
            use_cache: Whether to use cache.

        Returns:
        -------
            The retrieved record or None.

        """
        if cache_key and use_cache:
            cached = await self.cache_service.get(cache_key)
            if cached is not None:
                self.logger.debug(f"Cache hit for key: {cache_key}")
                return cached
            self.logger.debug(f"Cache miss for key: {cache_key}")

        record = await self.database_service.get_record(collection, filters)

        if record and cache_key and use_cache:
            await self.cache_service.set(cache_key, record)
            self.logger.debug(f"Cache updated for key: {cache_key}")

        return record

    async def set(
        self: DataService,
        collection: str,
        filters: dict[str, Any],
        data: dict[str, Any],
        cache_key: str | None = None,
        use_cache: bool = True,
    ) -> bool:
        """Set a record in both cache and DB (cache-first strategy).

        Args:
        ----
            collection: Name of the DB collection.
            filters: Query filters for DB.
            data: Data to upsert.
            cache_key: Optional cache key to update.
            use_cache: Whether to update cache.

        Returns:
        -------
            True if DB operation succeeded, False otherwise.

        """
        if cache_key and use_cache:
            await self.cache_service.set(cache_key, data)
            self.logger.debug(f"Set cache for key: {cache_key}")

        result = await self.database_service.upsert_record(collection, filters, data)
        self.logger.info(
            f"Set record in collection '{collection}' with filters {filters}"
        )
        return result

    async def delete(
        self: DataService,
        collection: str,
        filters: dict[str, Any],
        cache_key: str | None = None,
        use_cache: bool = True,
    ) -> bool:
        """Delete a record from both cache and DB.

        Args:
        ----
            collection: Name of the DB collection.
            filters: Query filters for DB.
            cache_key: Optional cache key to delete.
            use_cache: Whether to delete from cache.

        Returns:
        -------
            True if DB operation succeeded, False otherwise.

        """
        if cache_key and use_cache:
            await self.cache_service.delete(cache_key)
            self.logger.debug(f"Deleted cache for key: {cache_key}")

        result = await self.database_service.delete_record(collection, filters)
        self.logger.info(
            f"Deleted record in collection '{collection}' with filters {filters}"
        )
        return result

    async def clear_cache_pattern(self: DataService, pattern: str) -> int:
        """Clear all cache entries matching a pattern.

        Args:
        ----
            pattern: Pattern to match cache keys.

        Returns:
        -------
            Number of keys deleted.

        """
        deleted_count = await self.cache_service.clear_pattern(pattern)
        self.logger.info(
            f"Cleared cache keys matching pattern '{pattern}', count={deleted_count}"
        )
        return deleted_count

    async def execute_query(
        self: DataService, query: str, params: dict[str, Any]
    ) -> Any:
        """Execute a raw query on the database, bypassing cache.

        Args:
        ----
            query: Raw database query string.
            params: Query parameters.

        Returns:
        -------
            Query result.

        """
        result = await self.database_service.execute_query(query, params)
        self.logger.info(f"Executed raw DB query: {query} with params: {params}")
        return result
