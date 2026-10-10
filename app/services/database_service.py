from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.database import create_database
from app.services.base_service import BaseService

if TYPE_CHECKING:
    from app.core.interfaces.database_interface import DatabaseInterface
    from app.services.logger import Logger
    from config import Config


class DatabaseService(BaseService):
    """Thin, domain-agnostic wrapper around a DatabaseInterface backend.

    It selects the backend from config and logs failures. It deliberately knows
    nothing about users, roles or any other domain concept: seeding and schema
    belong to the data layer (``app.services.data``), caching to ``DataService``.
    """

    def __init__(
        self: DatabaseService,
        config: Config,
        logger: Logger,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize the DatabaseService.

        Args:
        ----
            config: The configuration to use.
            logger: The logger to use.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        """
        super().__init__(config, logger, *args, **kwargs)

        self.backend: DatabaseInterface = create_database(config, logger)

        self.logger.info("DatabaseService initialized", extra={"service": "DatabaseService"})

    # Payloads are never logged: records carry password hashes, tokens and PII.
    # Only the collection and the filter *keys* are safe to log.

    async def get_record(
        self: DatabaseService, collection: str, filters: dict[str, Any]
    ) -> dict | None:
        """Fetch a single record, or None if nothing matches."""
        try:
            return await self.backend.get_record(collection, filters)
        except Exception as e:
            self.logger.error(f"Error fetching record from {collection}: {e}")
            raise

    async def find_many(
        self: DatabaseService,
        collection: str,
        filters: dict[str, Any],
        *,
        limit: int | None = None,
        skip: int = 0,
        sort: list[tuple[str, int]] | None = None,
    ) -> list[dict]:
        """Fetch matching records (see ``DatabaseInterface.find_many``)."""
        try:
            return await self.backend.find_many(
                collection, filters, limit=limit, skip=skip, sort=sort
            )
        except Exception as e:
            self.logger.error(f"Error fetching records from {collection}: {e}")
            raise

    async def count(self: DatabaseService, collection: str, filters: dict[str, Any]) -> int:
        """Number of matching records."""
        return await self.backend.count(collection, filters)

    async def insert_record(self: DatabaseService, collection: str, data: dict[str, Any]) -> bool:
        """Insert a record; True if stored."""
        try:
            return await self.backend.insert_record(collection, data)
        except Exception as e:
            self.logger.error(f"Error inserting record into {collection}: {e}")
            raise

    async def update_record(
        self: DatabaseService,
        collection: str,
        filters: dict[str, Any],
        data: dict[str, Any],
    ) -> bool:
        """Update an existing record; False if no record matched (never inserts)."""
        try:
            return await self.backend.update_record(collection, filters, data)
        except Exception as e:
            self.logger.error(
                f"Error updating record in {collection} (filter keys: {sorted(filters)}): {e}"
            )
            raise

    async def update_many(
        self: DatabaseService, collection: str, filters: dict[str, Any], data: dict[str, Any]
    ) -> int:
        """Update every matching record at once; returns how many matched."""
        try:
            return await self.backend.update_many(collection, filters, data)
        except Exception as e:
            self.logger.error(f"Error updating records in {collection}: {e}")
            raise

    async def upsert_record(
        self: DatabaseService,
        collection: str,
        filters: dict[str, Any],
        data: dict[str, Any],
    ) -> bool:
        """Update the matching record, or insert it when none matches."""
        try:
            return await self.backend.upsert_record(collection, filters, data)
        except Exception as e:
            self.logger.error(
                f"Error upserting record in {collection} (filter keys: {sorted(filters)}): {e}"
            )
            raise

    async def delete_record(
        self: DatabaseService, collection: str, filters: dict[str, Any]
    ) -> bool:
        """Delete one matching record; True if something was deleted."""
        try:
            return await self.backend.delete_record(collection, filters)
        except Exception as e:
            self.logger.error(
                f"Error deleting record from {collection} (filter keys: {sorted(filters)}): {e}"
            )
            raise

    async def increment_field(
        self: DatabaseService,
        collection: str,
        filters: dict[str, Any],
        field: str,
        amount: int = 1,
    ) -> int | None:
        """Atomically add to a numeric field; returns the new value or None."""
        try:
            return await self.backend.increment_field(collection, filters, field, amount)
        except Exception as e:
            self.logger.error(
                f"Error incrementing {field} in {collection} (filter keys: {sorted(filters)}): {e}"
            )
            raise

    async def ensure_indexes(self, indexes: dict[str, list[dict[str, Any]]]) -> None:
        """Create the indexes declared by the data layer."""
        await self.backend.ensure_indexes(indexes)

    async def drop_indexes(self, indexes: dict[str, list[str]]) -> None:
        """Drop indexes that are no longer wanted."""
        await self.backend.drop_indexes(indexes)

    async def health_check(self: DatabaseService) -> bool:
        """Return True if the backend currently answers requests."""
        return await self.backend.health_check()

    @property
    def is_connected(self: DatabaseService) -> bool:
        """Whether the backend has opened its connection."""
        return self.backend.client is not None

    async def connect(self: DatabaseService) -> None:
        """Open the backend connection."""
        try:
            await self.backend.connect()
            self.logger.info("DatabaseService connected to backend.")
        except Exception as e:
            self.logger.error(f"DatabaseService failed to connect: {e}")
            raise

    async def close(self: DatabaseService) -> None:
        """Close the backend connection."""
        try:
            await self.backend.close()
            self.logger.info("DatabaseService closed backend connection.")
        except Exception as e:
            self.logger.error(f"DatabaseService failed to close: {e}")
            raise
