from __future__ import annotations
from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from app.core.interfaces.base_interface import BaseInterface

if TYPE_CHECKING:
    from app.services.logger.core import Logger


class DatabaseInterface(BaseInterface):
    def __init__(
        self: "DatabaseInterface",
        host: str,
        port: int,
        db_name: str,
        logger: "Logger",
        config: dict,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize DB client.

        Args:
        ----
            host: DB host
            port: DB port
            db_name: Database name
            logger: Logger instance
            config: Optional configuration dict
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        """
        self.config: dict = config
        self.logger: Logger = logger
        self.host: str = host
        self.port: int = port
        self.db_name: str = db_name
        self.db: object | None = None
        self.client: object | None = None

    @abstractmethod
    async def connect(self: "DatabaseInterface") -> None:
        """Connect to the database."""
        pass

    @abstractmethod
    async def close(self: "DatabaseInterface") -> None:
        """Close the connection."""
        pass

    @abstractmethod
    async def execute_query(
        self: "DatabaseInterface", query: str, params: dict[str, Any]
    ) -> Any:
        """Execute a raw query."""
        pass

    @abstractmethod
    async def get_record(
        self: "DatabaseInterface", collection: str, filters: dict[str, Any]
    ) -> dict | None:
        """Fetch a single record."""
        pass

    @abstractmethod
    async def find_many(
        self: "DatabaseInterface", collection: str, filters: dict[str, Any]
    ) -> list[dict]:
        """Fetch multiple records."""
        pass

    @abstractmethod
    async def initialize_db(self: "DatabaseInterface") -> None:
        """Initialize the database with required tables/collections."""
        pass

    @abstractmethod
    async def insert_record(
        self: "DatabaseInterface", collection: str, data: dict[str, Any]
    ) -> bool:
        """Insert a new record into the database."""
        pass

    @abstractmethod
    async def update_record(
        self: "DatabaseInterface",
        collection: str,
        filters: dict[str, Any],
        data: dict[str, Any],
    ) -> bool:
        """Update a record in the database."""
        pass

    @abstractmethod
    async def delete_record(
        self: "DatabaseInterface", collection: str, filters: dict[str, Any]
    ) -> bool:
        """Delete a record from the database."""
        pass

    @abstractmethod
    async def upsert_record(
        self: "DatabaseInterface",
        collection: str,
        filters: dict[str, Any],
        data: dict[str, Any],
    ) -> bool:
        """Upsert (update or insert) a record in the database."""
        pass


__all__ = [DatabaseInterface]
