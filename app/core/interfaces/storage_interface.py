"""Storage backend interface for file operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from app.services.logger import Logger
    from config import Config


STREAM_CHUNK_SIZE = 1024 * 1024  # bytes per piece when streaming


class StorageInterface(ABC):
    """Where file bytes live. Bring your own (S3, GCS, ...) by implementing this class and
    setting ``file_storage_backend`` to ``"package.module:YourStorage"``.

    Constructed with ``(config, logger)``. Paths are relative, ``/``-separated and chosen
    by the application; implementations must refuse any that escape their root.

    Implement the abstract methods; override the streaming and housekeeping methods below
    too when the backend can avoid holding whole files in memory (the defaults buffer).
    """

    def __init__(self, config: Config, logger: Logger) -> None:
        self.config = config
        self.logger = logger

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
    async def list(self: StorageInterface, prefix: str, *, recursive: bool = False) -> list[str]:
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

    # ---- optional: streaming and housekeeping (defaults are correct but buffer) ----
    async def save_stream(
        self: StorageInterface,
        file_path: str,
        chunks: AsyncIterator[bytes],
        *,
        overwrite: bool = False,
    ) -> bool:
        """Store the bytes yielded by ``chunks`` without holding them all in memory.

        If ``chunks`` raises, nothing may be left behind and the exception propagates.
        Returns False (like :meth:`save`) when the file exists and ``overwrite`` is off.
        """
        return await self.save(
            file_path, b"".join([chunk async for chunk in chunks]), overwrite=overwrite
        )

    async def open_stream(
        self: StorageInterface, file_path: str, *, chunk_size: int = STREAM_CHUNK_SIZE
    ) -> AsyncIterator[bytes] | None:
        """An iterator over the file's bytes, or None if it does not exist."""
        content = await self.read(file_path)
        if content is None:
            return None

        async def pieces() -> AsyncIterator[bytes]:
            for start in range(0, len(content), chunk_size):
                yield content[start : start + chunk_size]

        return pieces()

    async def download_url(
        self: StorageInterface,
        file_path: str,
        *,
        content_type: str,
        content_disposition: str,
        expires_in: int,
    ) -> str | None:
        """A short-lived URL the client can fetch directly (e.g. a presigned S3 URL) that
        serves the file with these response headers; None if the backend has none."""
        return None

    async def purge_older_than(self: StorageInterface, prefix: str, max_age_seconds: int) -> int:
        """Delete files under ``prefix`` last modified more than ``max_age_seconds`` ago
        (abandoned upload staging); returns how many. Backends with lifecycle rules may
        leave this as a no-op."""
        return 0


__all__ = ["STREAM_CHUNK_SIZE", "StorageInterface"]
