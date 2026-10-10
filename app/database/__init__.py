"""Database backends. Select with ``app_database_provider``: ``mongodb`` or
``package.module:YourDatabase`` (a ``DatabaseInterface`` implementation)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.interfaces.database_interface import DatabaseInterface
from app.core.plugins import load_backend_class

if TYPE_CHECKING:
    from app.services.logger import Logger
    from config import Config

BUILTIN_DATABASES = {"mongodb": "app.database.mongodb:MongoDB"}


def create_database(config: Config, logger: Logger) -> DatabaseInterface:
    """Instantiate the configured database backend."""
    cls = load_backend_class(config["app_database_provider"], BUILTIN_DATABASES, "database")
    return cls(config, logger)


__all__ = ["BUILTIN_DATABASES", "DatabaseInterface", "create_database"]
