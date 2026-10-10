"""Chunked (resumable) uploads.

Chunks are staged on the storage backend, not in the cache: Redis would hold up to a
whole file in memory per upload. The upload session record (owner, declared sizes) lives
in the cache, namespaced by user id, so one user can never read, extend or finish another
user's upload even if they know its id.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from app.services.base_service import BaseService

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from app.core.interfaces.storage_interface import StorageInterface
    from app.services.cache import CacheService
    from app.services.logger import Logger
    from config import Config

UPLOAD_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{8,64}")
STAGING_PREFIX = "_uploads"
MAX_CHUNKS_PER_UPLOAD = 10_000


class UploadSizeMismatchError(ValueError):
    """The staged chunks do not add up to the size the client declared."""


class ChunkedUploadHandler(BaseService):
    """Stage, validate and reassemble chunked uploads."""

    def __init__(
        self: ChunkedUploadHandler,
        logger: Logger,
        config: Config,
        cache_service: CacheService,
        storage_backend: StorageInterface,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize ChunkedUploadHandler.

        Args:
        ----
            logger: Logger instance.
            config: Configuration instance.
            cache_service: Holds the (small) upload session records.
            storage_backend: Holds the staged chunk bytes.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        """
        super().__init__(config, logger, *args, **kwargs)
        self.cache_service = cache_service
        self.storage = storage_backend
        self.max_total_size: int = config["file_max_size"]
        self.max_chunk_size: int = config["file_chunk_size"]
        self.upload_ttl: int = config["file_upload_ttl"]

    # ---- keys / paths -------------------------------------------------------
    @staticmethod
    def valid_upload_id(upload_id: str) -> bool:
        """Upload ids become path components, so only a safe alphabet is accepted."""
        return bool(UPLOAD_ID_PATTERN.fullmatch(upload_id))

    @staticmethod
    def _info_key(user_id: str, upload_id: str) -> str:
        return f"chunked_upload:{user_id}:{upload_id}"

    @staticmethod
    def _chunk_dir(user_id: str, upload_id: str) -> str:
        return f"{STAGING_PREFIX}/{user_id}/{upload_id}"

    def _chunk_path(self, user_id: str, upload_id: str, chunk_number: int) -> str:
        return f"{self._chunk_dir(user_id, upload_id)}/{chunk_number:06d}"

    # ---- session ------------------------------------------------------------
    async def get_upload_info(
        self: ChunkedUploadHandler, user_id: str, upload_id: str
    ) -> dict[str, Any] | None:
        """The caller's upload session, or None (also if it belongs to someone else)."""
        info = await self.cache_service.get(self._info_key(user_id, upload_id))
        return info if isinstance(info, dict) else None

    async def start_upload(
        self: ChunkedUploadHandler,
        *,
        user_id: str,
        upload_id: str,
        total_chunks: int,
        total_size: int,
        filename: str,
        content_type: str | None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create the session (idempotent for the same user and id).

        Raises:
        ------
            ValueError: If the id or the declared sizes are unacceptable.

        """
        if not self.valid_upload_id(upload_id):
            raise ValueError("upload_id must be 8-64 characters of letters, digits, '-' or '_'")
        if not 0 < total_size <= self.max_total_size:
            raise ValueError(f"total_size must be between 1 and {self.max_total_size} bytes")
        min_chunks = -(-total_size // self.max_chunk_size)
        if not min_chunks <= total_chunks <= min(total_size, MAX_CHUNKS_PER_UPLOAD):
            raise ValueError(
                f"total_chunks must be between {min_chunks} and "
                f"{min(total_size, MAX_CHUNKS_PER_UPLOAD)} for this file size"
            )

        info = {
            "upload_id": upload_id,
            "user_id": user_id,
            "total_chunks": total_chunks,
            "total_size": total_size,
            "filename": filename,
            "content_type": content_type or "application/octet-stream",
            "tags": tags or [],
            "metadata": metadata or {},
            "status": "in_progress",
        }
        # ``add`` (not ``set``): the session record lives only in the cache, so a cache
        # outage must fail the request (503) rather than pretend the upload was started, and
        # a second start for the same id must keep the first record.
        if await self.cache_service.add(self._info_key(user_id, upload_id), info, self.upload_ttl):
            return info
        return await self.get_upload_info(user_id, upload_id) or info

    # ---- chunks -------------------------------------------------------------
    async def received_chunks(
        self: ChunkedUploadHandler, user_id: str, upload_id: str
    ) -> list[int]:
        """Chunk numbers staged so far. Derived from storage, not a counter, so parallel
        chunk uploads cannot lose each other's updates."""
        paths = await self.storage.list(self._chunk_dir(user_id, upload_id))
        return sorted(int(p.rsplit("/", 1)[-1]) for p in paths)

    async def save_chunk(
        self: ChunkedUploadHandler,
        user_id: str,
        upload_id: str,
        chunk_number: int,
        chunk_data: bytes,
    ) -> bool:
        """Stage one chunk. Returns False if the session is unknown or the chunk is
        out of range or oversized."""
        info = await self.get_upload_info(user_id, upload_id)
        if not info or info.get("status") != "in_progress":
            return False
        if not 1 <= chunk_number <= info["total_chunks"]:
            return False
        # Chunks may be uneven (a short last one), but never more than twice the average the
        # session declared, so staged bytes stay near ``total_size`` whatever total_chunks says.
        average = -(-info["total_size"] // info["total_chunks"])
        if not chunk_data or len(chunk_data) > min(self.max_chunk_size, 2 * average):
            return False

        return await self.storage.save(
            self._chunk_path(user_id, upload_id, chunk_number),
            chunk_data,
            overwrite=True,  # a retried chunk replaces the earlier attempt
        )

    async def is_complete(self: ChunkedUploadHandler, user_id: str, upload_id: str) -> bool:
        """Whether every chunk 1..total_chunks has been staged."""
        info = await self.get_upload_info(user_id, upload_id)
        if not info:
            return False
        received = await self.received_chunks(user_id, upload_id)
        return received == list(range(1, info["total_chunks"] + 1))

    async def open_assembled(
        self: ChunkedUploadHandler, user_id: str, upload_id: str
    ) -> AsyncIterator[bytes] | None:
        """The chunks in order as one stream; None if the upload is unknown or incomplete.

        Raises ``UploadSizeMismatchError`` at the end of the stream if the bytes do not add
        up to the declared size, which makes the consumer discard what it stored.
        """
        info = await self.get_upload_info(user_id, upload_id)
        if not info or not await self.is_complete(user_id, upload_id):
            return None

        async def pieces() -> AsyncIterator[bytes]:
            total = 0
            for number in range(1, info["total_chunks"] + 1):
                chunk = await self.storage.open_stream(self._chunk_path(user_id, upload_id, number))
                if chunk is None:
                    raise UploadSizeMismatchError(f"chunk {number} disappeared")
                async for piece in chunk:
                    total += len(piece)
                    yield piece
            if total != info["total_size"]:
                self.logger.warning(
                    "Chunked upload size mismatch",
                    extra={
                        "service": "ChunkedUploadHandler",
                        "upload_id": upload_id,
                        "declared": info["total_size"],
                        "actual": total,
                    },
                )
                raise UploadSizeMismatchError("size does not match what was declared")

        return pieces()

    async def purge_abandoned(self: ChunkedUploadHandler) -> int:
        """Delete staged chunks older than the session lifetime (uploads nobody finished).

        Their session records have expired by then, so no chunk can be added or assembled.
        """
        return await self.storage.purge_older_than(STAGING_PREFIX, self.upload_ttl)

    async def cleanup(self: ChunkedUploadHandler, user_id: str, upload_id: str) -> None:
        """Delete staged chunks and the session record."""
        for number in await self.received_chunks(user_id, upload_id):
            await self.storage.delete(self._chunk_path(user_id, upload_id, number))
        await self.cache_service.delete(self._info_key(user_id, upload_id))
