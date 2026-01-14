"""Local filesystem storage backend."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiofiles
from aiofiles.os import remove, stat

from app.core.interfaces.storage_interface import StorageInterface

if TYPE_CHECKING:
    from app.services.logger.core import Logger


class LocalStorage(StorageInterface):
    """Local filesystem storage implementation."""

    def __init__(
        self: LocalStorage,
        logger: Logger,
        config: dict,
        base_path: str | None = None,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize local storage backend.

        Args:
        ----
            logger: Logger instance.
            config: Configuration dictionary.
            base_path: Base directory for file storage.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        """
        super().__init__(logger, config, *args, **kwargs)
        self.base_path = Path(
            base_path or config.get("file_storage_base_path", "uploads")
        )
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self: LocalStorage, file_path: str) -> Path:
        """Get full filesystem path for a file.

        Args:
        ----
            file_path: Relative file path.

        Returns:
        -------
            Full Path object.

        Raises:
        ------
            ValueError: If path traversal is detected.

        """
        # Normalize path to prevent directory traversal
        # Remove any leading slashes and normalize separators
        normalized_path = file_path.lstrip("/").replace("\\", "/")

        # Check for path traversal patterns
        if ".." in normalized_path or normalized_path.startswith("/"):
            raise ValueError("Path traversal detected")

        # Build the full path
        full_path = self.base_path / normalized_path

        # Resolve both paths to absolute and check
        try:
            base_resolved = str(self.base_path.resolve())
            full_resolved = str(full_path.resolve())

            # Check if resolved path is within base path
            if not full_resolved.startswith(base_resolved):
                raise ValueError("Path traversal detected")
        except (OSError, RuntimeError):
            # If resolve fails (e.g., path doesn't exist), check manually
            # Ensure no parent directory traversal
            parts = normalized_path.split("/")
            if ".." in parts or any(part.startswith("..") for part in parts):
                raise ValueError("Path traversal detected")

        return full_path

    async def save(
        self: LocalStorage,
        file_path: str,
        content: bytes,
        *,
        overwrite: bool = False,
    ) -> bool:
        """Save file content to local filesystem.

        Args:
        ----
            file_path: Relative path where file should be stored.
            content: File content as bytes.
            overwrite: Whether to overwrite existing file.

        Returns:
        -------
            True if successful, False otherwise.

        """
        try:
            full_path = self._get_full_path(file_path)

            if not overwrite and await self.exists(file_path):
                self.logger.warning(
                    f"File already exists: {file_path}",
                    extra={"service": "LocalStorage"},
                )
                return False

            full_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(full_path, "wb") as f:
                await f.write(content)

            self.logger.debug(
                f"Saved file: {file_path}",
                extra={"service": "LocalStorage", "size": len(content)},
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to save file {file_path}: {e}",
                extra={"service": "LocalStorage"},
            )
            return False

    async def read(self: LocalStorage, file_path: str) -> bytes | None:
        """Read file content from local filesystem.

        Args:
        ----
            file_path: Relative path to file.

        Returns:
        -------
            File content as bytes, or None if not found.

        """
        try:
            full_path = self._get_full_path(file_path)

            if not await self.exists(file_path):
                return None

            async with aiofiles.open(full_path, "rb") as f:
                content = await f.read()

            self.logger.debug(
                f"Read file: {file_path}",
                extra={"service": "LocalStorage", "size": len(content)},
            )
            return content

        except Exception as e:
            self.logger.error(
                f"Failed to read file {file_path}: {e}",
                extra={"service": "LocalStorage"},
            )
            return None

    async def delete(self: LocalStorage, file_path: str) -> bool:
        """Delete file from local filesystem.

        Args:
        ----
            file_path: Relative path to file.

        Returns:
        -------
            True if successful, False otherwise.

        """
        try:
            full_path = self._get_full_path(file_path)

            if not await self.exists(file_path):
                self.logger.warning(
                    f"File not found for deletion: {file_path}",
                    extra={"service": "LocalStorage"},
                )
                return False

            await remove(full_path)

            self.logger.debug(
                f"Deleted file: {file_path}",
                extra={"service": "LocalStorage"},
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to delete file {file_path}: {e}",
                extra={"service": "LocalStorage"},
            )
            return False

    async def exists(self: LocalStorage, file_path: str) -> bool:
        """Check if file exists in local filesystem.

        Args:
        ----
            file_path: Relative path to file.

        Returns:
        -------
            True if file exists, False otherwise.

        """
        try:
            full_path = self._get_full_path(file_path)
            return full_path.exists() and full_path.is_file()

        except Exception:
            return False

    async def get_url(
        self: LocalStorage, file_path: str, *, expires_in: int | None = None
    ) -> str:
        """Get URL for accessing file (local filesystem returns relative path).

        Args:
        ----
            file_path: Relative path to file.
            expires_in: Not used for local storage.

        Returns:
        -------
            Relative URL path.

        """
        return f"/files/{file_path}"

    async def list(
        self: LocalStorage, prefix: str, *, recursive: bool = False
    ) -> list[str]:
        """List files in local filesystem.

        Args:
        ----
            prefix: Path prefix to list files under.
            recursive: Whether to list recursively.

        Returns:
        -------
            List of relative file paths.

        """
        try:
            full_prefix = self._get_full_path(prefix)
            files = []

            if not full_prefix.exists():
                return []

            if recursive:
                for root, dirs, filenames in os.walk(full_prefix):
                    for filename in filenames:
                        file_path = Path(root) / filename
                        relative_path = file_path.relative_to(self.base_path)
                        files.append(str(relative_path))
            else:
                for item in full_prefix.iterdir():
                    if item.is_file():
                        relative_path = item.relative_to(self.base_path)
                        files.append(str(relative_path))

            return files

        except Exception as e:
            self.logger.error(
                f"Failed to list files with prefix {prefix}: {e}",
                extra={"service": "LocalStorage"},
            )
            return []

    async def get_size(self: LocalStorage, file_path: str) -> int:
        """Get file size in bytes.

        Args:
        ----
            file_path: Relative path to file.

        Returns:
        -------
            File size in bytes.

        """
        try:
            full_path = self._get_full_path(file_path)
            if not await self.exists(file_path):
                return 0
            file_stat = await stat(full_path)
            return file_stat.st_size

        except Exception as e:
            self.logger.error(
                f"Failed to get file size for {file_path}: {e}",
                extra={"service": "LocalStorage"},
            )
            return 0

    def compute_hash(self: LocalStorage, content: bytes) -> str:
        """Compute SHA256 hash of content.

        Args:
        ----
            content: File content as bytes.

        Returns:
        -------
            SHA256 hash as hex string.

        """
        return hashlib.sha256(content).hexdigest()


__all__ = ["LocalStorage"]
