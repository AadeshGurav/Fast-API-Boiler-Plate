from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from app.services.base_service import BaseService
from app.services.logger import Logger
from config import Config

from .files_ops import FilesOps
from .migrations import run_migrations
from .oauth_ops import OAuthOps
from .policies import CachePolicy
from .schema import COLLECTION_INDEXES
from .sessions_ops import SessionsOps
from .temp_permissions_ops import TemporaryPermissionsOps
from .users_ops import UsersOps


def _convert_datetime_strings(obj: Any) -> Any:
    """Recursively turn ISO strings under ``*_at`` / ``*_date`` / ``exp`` keys into datetimes.

    The cache stores JSON, which flattens datetimes to strings; reads from cache and
    database must hand callers the same types.
    """
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            if isinstance(value, str) and (
                key.endswith("_at") or key.endswith("_date") or key == "exp"
            ):
                try:
                    result[key] = datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    result[key] = value
            else:
                result[key] = _convert_datetime_strings(value)
        return result
    if isinstance(obj, list):
        return [_convert_datetime_strings(item) for item in obj]
    return obj


def _normalize_record(record: dict[str, Any] | None) -> dict[str, Any] | None:
    """Give cached and database records the same shape; collection-agnostic.

    Collection-specific rules (e.g. user fields) live in that collection's ops.
    """
    if not record:
        return None
    return _convert_datetime_strings(record)


def _default_cache_key(collection: str, filters: dict[str, Any]) -> str:
    """Generate default cache key from collection and filters.

    Args:
    ----
        collection: Collection name.
        filters: Filter dictionary.

    Returns:
    -------
        MD5 hash of collection and filters as cache key.

    """
    payload = json.dumps([collection, filters], sort_keys=True, default=str)
    return hashlib.md5(usedforsecurity=False, string=payload.encode()).hexdigest()


class DataService(BaseService):
    """Core data access service with cache-aware CRUD operations.

    This class is intentionally small and delegates domain logic to ops modules.
    """

    def __init__(
        self: DataService,
        config: Config,
        logger: Logger,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize DataService.

        Args:
        ----
            config: Configuration instance.
            logger: Logger instance.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        """
        super().__init__(config, logger, *args, **kwargs)
        self.users = UsersOps(self)
        self.sessions = SessionsOps(self)
        self.temp_permissions = TemporaryPermissionsOps(self)
        self.oauth = OAuthOps(self)
        self.files = FilesOps(self)

        self.logger.info("DataService initialized", extra={"service": "DataService"})

    # ---- Lifecycle -----------------------------------------------------
    async def connect(self: DataService) -> None:
        """Connect to database and cache backends.

        Returns
        -------
            None

        """
        await self.database_service.connect()
        await self.cache_service.connect()
        await run_migrations(self.database_service, self.logger)
        await self.database_service.ensure_indexes(COLLECTION_INDEXES)
        self.logger.info("DataService: All backends connected and initialized.")

    async def close(self: DataService) -> None:
        """Close database and cache backends.

        Returns
        -------
            None

        """
        await self.database_service.close()
        await self.cache_service.close()
        self.logger.info("DataService: All backends closed.")

    @property
    def is_connected(self: DataService) -> dict[str, bool]:
        """Whether each backend has opened its connection."""
        return {
            "database": self.database_service.is_connected,
            "cache": self.cache_service.is_connected,
        }

    # ---- Core CRUD with cache policy ----------------------------------
    async def get(
        self: DataService,
        collection: str,
        filters: dict[str, Any],
        *,
        key: str | None = None,
        policy: CachePolicy = CachePolicy.AUTO,
    ) -> dict[str, Any] | None:
        """Get a record from collection with cache policy.

        Args:
        ----
            collection: Collection name.
            filters: Filter dictionary.
            key: Optional cache key.
            policy: Cache policy to use.

        Returns:
        -------
            Record dictionary or None if not found.

        """
        cache_key = key or _default_cache_key(collection, filters)

        if policy == CachePolicy.CACHE_ONLY:
            cached = await self.cache_service.get(cache_key)
            return _normalize_record(cached)

        if policy == CachePolicy.AUTO:
            cached = await self.cache_service.get(cache_key)
            if cached is not None:
                return _normalize_record(cached)

        # DB_ONLY or cache miss
        record = await self.database_service.get_record(collection, filters)
        if record is not None and policy != CachePolicy.DB_ONLY:
            await self.cache_service.set(cache_key, record)
        return _normalize_record(record)

    async def find_many(
        self: DataService,
        collection: str,
        filters: dict[str, Any],
        *,
        key: str | None = None,
        policy: CachePolicy = CachePolicy.DB_ONLY,
        limit: int | None = None,
        skip: int = 0,
        sort: list[tuple[str, int]] | None = None,
    ) -> list[dict]:
        """Find multiple records from collection with cache policy.

        Args:
        ----
            collection: Collection name.
            filters: Filter dictionary.
            key: Optional cache key.
            policy: Cache policy to use.

        Returns:
        -------
            List of record dictionaries.

        """
        # By default, lists come from DB to avoid cache stampede complexity
        if policy == CachePolicy.CACHE_ONLY:
            cached = await self.cache_service.get(key or _default_cache_key(collection, filters))
            if cached:
                return [_normalize_record(record) for record in cached]
            return []
        # Lists are never read through the cache: any write to the collection would
        # leave them stale and there is no per-collection invalidation. CACHE_ONLY
        # remains for callers that manage their own list keys.
        records = await self.database_service.find_many(
            collection, filters, limit=limit, skip=skip, sort=sort
        )
        # Normalize all records before returning
        return [_normalize_record(record) for record in (records or [])]

    async def set(
        self: DataService,
        collection: str,
        filters: dict[str, Any],
        data: dict[str, Any],
        *,
        key: str | None = None,
        policy: CachePolicy = CachePolicy.AUTO,
        ttl: int | None = None,
    ) -> bool:
        """Set/upsert a record in collection with cache policy.

        Args:
        ----
            collection: Collection name.
            filters: Filter dictionary.
            data: Data dictionary to set.
            key: Optional cache key.
            policy: Cache policy to use.
            ttl: Optional TTL for cache.

        Returns:
        -------
            True if successful, False otherwise.

        """
        cache_key = key or _default_cache_key(collection, filters)

        if policy == CachePolicy.CACHE_ONLY:
            await self.cache_service.set(cache_key, data, ttl)
            return True

        # Write to DB
        result = await self.database_service.upsert_record(collection, filters, data)
        if result and policy != CachePolicy.DB_ONLY:
            # ``data`` may be a partial update, so caching it would serve a
            # truncated record. Drop the entry; the next read repopulates it.
            await self.cache_service.delete(cache_key)
        return result

    async def count(self: DataService, collection: str, filters: dict[str, Any]) -> int:
        """Number of records matching ``filters`` (always from the database)."""
        return await self.database_service.count(collection, filters)

    async def insert(self: DataService, collection: str, data: dict[str, Any]) -> bool:
        """Insert a new record (append-only data such as audit logs); never cached."""
        return await self.database_service.insert_record(collection, data)

    async def increment(
        self: DataService,
        collection: str,
        filters: dict[str, Any],
        field: str,
        amount: int = 1,
        *,
        key: str | None = None,
    ) -> int | None:
        """Atomically add to a numeric field and drop the record's cache entry.

        Returns:
        -------
            The new value, or None if no record matched.

        """
        value = await self.database_service.increment_field(collection, filters, field, amount)
        await self.cache_service.delete(key or _default_cache_key(collection, filters))
        return value

    async def update(
        self: DataService,
        collection: str,
        filters: dict[str, Any],
        data: dict[str, Any],
        *,
        key: str | None = None,
        policy: CachePolicy = CachePolicy.AUTO,
    ) -> bool:
        """Update an existing record; returns False (and writes nothing) if absent.

        Unlike ``set`` this never creates a record, so a stale or mistyped ID cannot
        leave a half-empty document behind.

        Args:
        ----
            collection: Collection name.
            filters: Filter selecting the record.
            data: Fields to change.
            key: Optional cache key.
            policy: Cache policy to use.

        Returns:
        -------
            True if a record matched and was updated.

        """
        result = await self.database_service.update_record(collection, filters, data)
        if result and policy != CachePolicy.DB_ONLY:
            await self.cache_service.delete(key or _default_cache_key(collection, filters))
        return result

    async def update_many(
        self: DataService,
        collection: str,
        filters: dict[str, Any],
        data: dict[str, Any],
    ) -> int:
        """Apply ``data`` to every matching record in one round trip; returns the match count.

        Bulk writes bypass the record cache, so use them only on collections read with
        ``CachePolicy.DB_ONLY`` (or whose cached entries are short-lived).
        """
        return await self.database_service.update_many(collection, filters, data)

    async def delete(
        self: DataService,
        collection: str,
        filters: dict[str, Any],
        *,
        key: str | None = None,
        policy: CachePolicy = CachePolicy.AUTO,
    ) -> bool:
        """Delete a record from collection with cache policy.

        Args:
        ----
            collection: Collection name.
            filters: Filter dictionary.
            key: Optional cache key.
            policy: Cache policy to use.

        Returns:
        -------
            True if successful, False otherwise.

        """
        cache_key = key or _default_cache_key(collection, filters)

        if policy == CachePolicy.CACHE_ONLY:
            await self.cache_service.delete(cache_key)
            return True

        result = await self.database_service.delete_record(collection, filters)
        if result and policy != CachePolicy.DB_ONLY:
            await self.cache_service.delete(cache_key)
        return result


__all__ = ["DataService"]
