from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.logger import Logger
    from config import Config


class DuplicateRecordError(ValueError):
    """A write would break a unique index. Backends raise this, never a driver exception,
    so callers can tell "already exists" from "the database failed"."""


class DatabaseInterface(ABC):
    """Contract for a database backend. Bring your own by implementing it and setting
    ``app_database_provider`` to ``"package.module:YourClass"``.

    Constructed with ``(config, logger)``; read your own settings from ``config``. Records
    are plain dicts; ``id`` is the application-level identifier.
    """

    def __init__(self, config: Config, logger: Logger) -> None:
        self.config = config
        self.logger = logger
        self.client: object | None = None  # set by connect(); None while disconnected

    @abstractmethod
    async def connect(self: DatabaseInterface) -> None:
        """Connect to the database."""
        pass

    @abstractmethod
    async def close(self: DatabaseInterface) -> None:
        """Close the connection."""
        pass

    @abstractmethod
    async def increment_field(
        self: DatabaseInterface,
        collection: str,
        filters: dict[str, Any],
        field: str,
        amount: int = 1,
    ) -> int | None:
        """Atomically add ``amount`` to a numeric field.

        Returns the new value, or None if no record matched. Must be atomic: two
        concurrent callers must never observe the same result.
        """
        pass

    @abstractmethod
    async def drop_indexes(self, indexes: dict[str, list[str]]) -> None:
        """Drop the named indexes per collection; missing ones are not an error."""

    @abstractmethod
    async def health_check(self: DatabaseInterface) -> bool:
        """Return True if the backend currently answers requests."""
        pass

    @abstractmethod
    async def ensure_indexes(self, indexes: dict[str, list[dict[str, Any]]]) -> None:
        """Create the indexes the application declares, per collection.

        The backend knows *how* to build an index; the data layer owns *which*
        indexes exist. Each spec is ``{"keys": [(field, direction), ...],
        **options}`` (options such as ``unique``, ``sparse``,
        ``expireAfterSeconds``).
        Backends without indexes make this a no-op.
        """
        pass

    @abstractmethod
    async def get_record(
        self: DatabaseInterface, collection: str, filters: dict[str, Any]
    ) -> dict | None:
        """Fetch a single record."""
        pass

    @abstractmethod
    async def find_many(
        self: DatabaseInterface,
        collection: str,
        filters: dict[str, Any],
        *,
        limit: int | None = None,
        skip: int = 0,
        sort: list[tuple[str, int]] | None = None,
    ) -> list[dict]:
        """Fetch matching records; ``sort`` is ``[(field, 1 or -1)]``.

        Without ``limit`` an implementation must still cap the result (a safety net against
        loading a whole collection); page with ``limit``/``skip``.
        """
        pass

    @abstractmethod
    async def count(self: DatabaseInterface, collection: str, filters: dict[str, Any]) -> int:
        """Number of matching records."""
        pass

    @abstractmethod
    async def initialize_db(self: DatabaseInterface) -> None:
        """Initialize the database with required tables/collections."""
        pass

    @abstractmethod
    async def insert_record(self: DatabaseInterface, collection: str, data: dict[str, Any]) -> bool:
        """Insert a new record; raise ``DuplicateRecordError`` on a unique-index violation."""
        pass

    @abstractmethod
    async def update_record(
        self: DatabaseInterface,
        collection: str,
        filters: dict[str, Any],
        data: dict[str, Any],
    ) -> bool:
        """Update a record in the database."""
        pass

    @abstractmethod
    async def update_many(
        self: DatabaseInterface, collection: str, filters: dict[str, Any], data: dict[str, Any]
    ) -> int:
        """Apply ``data`` to every matching record in one operation; returns how many matched."""
        pass

    @abstractmethod
    async def delete_record(
        self: DatabaseInterface, collection: str, filters: dict[str, Any]
    ) -> bool:
        """Delete a record from the database."""
        pass

    @abstractmethod
    async def upsert_record(
        self: DatabaseInterface,
        collection: str,
        filters: dict[str, Any],
        data: dict[str, Any],
    ) -> bool:
        """Upsert (update or insert) a record in the database."""
        pass


__all__ = ["DatabaseInterface"]
