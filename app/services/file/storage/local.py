"""Local filesystem storage backend."""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import aiofiles
from aiofiles.os import path as aio_path
from aiofiles.os import remove, replace, stat

from app.core.interfaces.storage_interface import STREAM_CHUNK_SIZE, StorageInterface

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from app.services.logger import Logger
    from config import Config


class LocalStorage(StorageInterface):
    """Local filesystem storage implementation."""

    def __init__(self, config: Config, logger: Logger, base_path: str | None = None) -> None:
        super().__init__(config, logger)
        self.base_path = Path(base_path or config["file_storage_base_path"])
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
        relative = Path(file_path.replace("\\", "/").lstrip("/"))
        base = self.base_path.resolve()
        full_path = (base / relative).resolve()

        # Resolving first means symlinks and ".." segments are both accounted for;
        # a string-prefix test would accept a sibling like "<base>_evil".
        if not full_path.is_relative_to(base):
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
            return await aio_path.isfile(self._get_full_path(file_path))

        except Exception:
            return False

    async def get_url(self: LocalStorage, file_path: str, *, expires_in: int | None = None) -> str:
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

    async def list(self: LocalStorage, prefix: str, *, recursive: bool = False) -> list[str]:
        """Relative paths of the files under ``prefix`` (directly, or recursively)."""
        try:
            return await asyncio.to_thread(self._list_sync, self._get_full_path(prefix), recursive)
        except Exception as e:
            self.logger.error(
                f"Failed to list files with prefix {prefix}: {e}",
                extra={"service": "LocalStorage"},
            )
            return []

    def _list_sync(self, directory: Path, recursive: bool) -> list[str]:
        if not directory.is_dir():
            return []
        root = self.base_path.resolve()
        if recursive:
            found = (Path(d) / name for d, _, names in os.walk(directory) for name in names)
        else:
            found = (item for item in directory.iterdir() if item.is_file())
        return [str(item.relative_to(root)) for item in found]

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

    # ---- streaming and housekeeping -------------------------------------------------
    async def save_stream(
        self: LocalStorage,
        file_path: str,
        chunks: AsyncIterator[bytes],
        *,
        overwrite: bool = False,
    ) -> bool:
        """Write to a sibling temp file, then rename: readers never see a partial file and
        a failing ``chunks`` leaves nothing behind."""
        full_path = self._get_full_path(file_path)
        if not overwrite and await self.exists(file_path):
            return False
        full_path.parent.mkdir(parents=True, exist_ok=True)
        partial = full_path.with_name(f".{full_path.name}.{uuid.uuid4().hex}.partial")
        try:
            async with aiofiles.open(partial, "wb") as f:
                async for chunk in chunks:
                    await f.write(chunk)
            await replace(partial, full_path)
        except BaseException:
            if await aio_path.exists(partial):
                await remove(partial)
            raise
        return True

    async def open_stream(
        self: LocalStorage, file_path: str, *, chunk_size: int = STREAM_CHUNK_SIZE
    ) -> AsyncIterator[bytes] | None:
        """Read the file piece by piece (None if it does not exist)."""
        if not await self.exists(file_path):
            return None
        full_path = self._get_full_path(file_path)

        async def pieces() -> AsyncIterator[bytes]:
            async with aiofiles.open(full_path, "rb") as f:
                while piece := await f.read(chunk_size):
                    yield piece

        return pieces()

    async def purge_older_than(self: LocalStorage, prefix: str, max_age_seconds: int) -> int:
        """Delete stale files (and partial writes) under ``prefix``; prune empty folders."""
        return await asyncio.to_thread(
            self._purge_sync, self._get_full_path(prefix), time.time() - max_age_seconds
        )

    @staticmethod
    def _purge_sync(directory: Path, cutoff: float) -> int:
        removed = 0
        for folder, _, names in os.walk(directory, topdown=False):
            for name in names:
                path = Path(folder) / name
                try:
                    if path.stat().st_mtime < cutoff:
                        path.unlink()
                        removed += 1
                except FileNotFoundError:
                    continue  # another worker's janitor got there first
            try:
                if Path(folder) != directory:
                    Path(folder).rmdir()  # only succeeds when empty
            except OSError:
                pass  # not empty: still holds fresh files
        return removed


__all__ = ["LocalStorage"]
