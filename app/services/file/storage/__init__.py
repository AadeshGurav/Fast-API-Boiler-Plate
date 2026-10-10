"""Storage backends. Select with ``file_storage_backend``: ``local``, ``s3`` or
``package.module:YourStorage`` (a ``StorageInterface`` implementation)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.interfaces.storage_interface import StorageInterface
from app.core.plugins import load_backend_class

if TYPE_CHECKING:
    from app.services.logger import Logger
    from config import Config

BUILTIN_STORAGES = {
    "local": "app.services.file.storage.local:LocalStorage",
    "s3": "app.services.file.storage.s3:S3Storage",
}


def create_storage(config: Config, logger: Logger) -> StorageInterface:
    """Instantiate the configured storage backend."""
    cls = load_backend_class(config["file_storage_backend"], BUILTIN_STORAGES, "storage")
    return cls(config, logger)


__all__ = ["BUILTIN_STORAGES", "StorageInterface", "create_storage"]
