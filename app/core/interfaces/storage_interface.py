"""Storage backend interface for file operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from app.core.interfaces.base_interface import BaseInterface

if TYPE_CHECKING:
    from app.services.logger.core import Logger


class StorageInterface(BaseInterface):
    """Abstract interface for storage backends."""

    def __init__(
        self: StorageInterface,
        logger: Logger,
        config: dict,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize storage backend.

        Args:
        ----
            logger: Logger instance.
            config: Configuration dictionary.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        """
        super().__init__(logger, config, *args, **kwargs)

    @abstractmethod
    async def save(
        self: StorageInterface,
        file_path: str,
        content: bytes,
        *,
        overwrite: bool = False,
    ) -> bool:
        """Save file content to storage.

        Args:
        ----
            file_path: Relative path where file should be stored.
            content: File content as bytes.
            overwrite: Whether to overwrite existing file.

        Returns:
        -------
            True if successful, False otherwise.

        """
        pass

    @abstractmethod
    async def read(self: StorageInterface, file_path: str) -> bytes | None:
        """Read file content from storage.

        Args:
        ----
            file_path: Relative path to file.

        Returns:
        -------
            File content as bytes, or None if not found.

        """
        pass

    @abstractmethod
    async def delete(self: StorageInterface, file_path: str) -> bool:
        """Delete file from storage.

        Args:
        ----
            file_path: Relative path to file.

        Returns:
        -------
            True if successful, False otherwise.

        """
        pass

    @abstractmethod
    async def exists(self: StorageInterface, file_path: str) -> bool:
        """Check if file exists in storage.

        Args:
        ----
            file_path: Relative path to file.

        Returns:
        -------
            True if file exists, False otherwise.

        """
        pass

    @abstractmethod
    async def get_url(
        self: StorageInterface, file_path: str, *, expires_in: int | None = None
    ) -> str:
        """Get URL for accessing file.

        Args:
        ----
            file_path: Relative path to file.
            expires_in: Optional expiration time in seconds for signed URLs.

        Returns:
        -------
            URL string for accessing the file.

        """
        pass

    @abstractmethod
    async def list(
        self: StorageInterface, prefix: str, *, recursive: bool = False
    ) -> list[str]:
        """List files in storage.

        Args:
        ----
            prefix: Path prefix to list files under.
            recursive: Whether to list recursively.

        Returns:
        -------
            List of file paths.

        """
        pass

    @abstractmethod
    async def get_size(self: StorageInterface, file_path: str) -> int:
        """Get file size in bytes.

        Args:
        ----
            file_path: Relative path to file.

        Returns:
        -------
            File size in bytes.

        """
        pass


__all__ = ["StorageInterface"]

