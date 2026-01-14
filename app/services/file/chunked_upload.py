"""Chunked upload handler for large files."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from app.services.base_service import BaseService

if TYPE_CHECKING:
    from app.services.cache import CacheService
    from app.services.logger import Logger
    from config import Config


class ChunkedUploadHandler(BaseService):
    """Handler for chunked file uploads."""

    def __init__(
        self: ChunkedUploadHandler,
        logger: Logger,
        config: Config,
        cache_service: CacheService,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize ChunkedUploadHandler.

        Args:
        ----
            logger: Logger instance.
            config: Configuration instance.
            cache_service: CacheService instance.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        """
        super().__init__(config, logger, *args, **kwargs)
        self.cache_service = cache_service
        self.chunk_size = config.get("file_chunk_size", 5242880)
        self.upload_ttl = config.get("file_upload_ttl", 3600)

        self.logger.info(
            "ChunkedUploadHandler initialized",
            extra={"service": "ChunkedUploadHandler"},
        )

    def _get_upload_key(self: ChunkedUploadHandler, upload_id: str) -> str:
        """Get Redis key for upload session.

        Args:
        ----
            upload_id: Upload session ID.

        Returns:
        -------
            Redis key string.

        """
        return f"chunked_upload:{upload_id}"

    def _get_chunk_key(
        self: ChunkedUploadHandler, upload_id: str, chunk_number: int
    ) -> str:
        """Get Redis key for chunk data.

        Args:
        ----
            upload_id: Upload session ID.
            chunk_number: Chunk sequence number.

        Returns:
        -------
            Redis key string.

        """
        return f"chunked_upload:{upload_id}:chunk:{chunk_number}"

    async def start_upload(
        self: ChunkedUploadHandler,
        upload_id: str,
        total_chunks: int,
        total_size: int,
        filename: str,
        content_type: str | None = None,
        user_id: str | None = None,
    ) -> bool:
        """Start a new chunked upload session.

        Args:
        ----
            upload_id: Unique upload session ID.
            total_chunks: Total number of chunks expected.
            total_size: Total file size in bytes.
            filename: Original filename.
            content_type: Optional MIME type.
            user_id: Optional user ID.

        Returns:
        -------
            True if successful, False otherwise.

        """
        upload_info = {
            "upload_id": upload_id,
            "total_chunks": total_chunks,
            "total_size": total_size,
            "filename": filename,
            "content_type": content_type,
            "user_id": user_id,
            "chunks_received": [],
            "status": "in_progress",
        }

        key = self._get_upload_key(upload_id)
        await self.cache_service.set(key, json.dumps(upload_info), ttl=self.upload_ttl)

        self.logger.info(
            f"Started chunked upload: {upload_id}",
            extra={"service": "ChunkedUploadHandler"},
        )
        return True

    async def save_chunk(
        self: ChunkedUploadHandler,
        upload_id: str,
        chunk_number: int,
        chunk_data: bytes,
    ) -> bool:
        """Save a chunk of data.

        Args:
        ----
            upload_id: Upload session ID.
            chunk_number: Chunk sequence number.
            chunk_data: Chunk content as bytes.

        Returns:
        -------
            True if successful, False otherwise.

        """
        upload_info = await self.get_upload_info(upload_id)
        if not upload_info:
            return False

        if upload_info.get("status") != "in_progress":
            return False

        chunk_key = self._get_chunk_key(upload_id, chunk_number)
        await self.cache_service.set(chunk_key, chunk_data, ttl=self.upload_ttl)

        chunks_received = upload_info.get("chunks_received", [])
        if chunk_number not in chunks_received:
            chunks_received.append(chunk_number)
            chunks_received.sort()

        upload_info["chunks_received"] = chunks_received
        key = self._get_upload_key(upload_id)
        await self.cache_service.set(key, json.dumps(upload_info), ttl=self.upload_ttl)

        self.logger.debug(
            f"Saved chunk {chunk_number} for upload {upload_id}",
            extra={"service": "ChunkedUploadHandler"},
        )
        return True

    async def get_chunk(
        self: ChunkedUploadHandler, upload_id: str, chunk_number: int
    ) -> bytes | None:
        """Retrieve a chunk of data.

        Args:
        ----
            upload_id: Upload session ID.
            chunk_number: Chunk sequence number.

        Returns:
        -------
            Chunk data as bytes, or None if not found.

        """
        chunk_key = self._get_chunk_key(upload_id, chunk_number)
        chunk_data = await self.cache_service.get(chunk_key)

        if isinstance(chunk_data, bytes):
            return chunk_data

        if isinstance(chunk_data, str):
            return chunk_data.encode()

        return None

    async def get_upload_info(
        self: ChunkedUploadHandler, upload_id: str
    ) -> dict[str, Any] | None:
        """Get upload session information.

        Args:
        ----
            upload_id: Upload session ID.

        Returns:
        -------
            Upload info dictionary or None if not found.

        """
        key = self._get_upload_key(upload_id)
        info_data = await self.cache_service.get(key)

        if isinstance(info_data, str):
            try:
                return json.loads(info_data)
            except json.JSONDecodeError:
                return None

        return None

    async def is_upload_complete(self: ChunkedUploadHandler, upload_id: str) -> bool:
        """Check if all chunks have been received.

        Args:
        ----
            upload_id: Upload session ID.

        Returns:
        -------
            True if complete, False otherwise.

        """
        upload_info = await self.get_upload_info(upload_id)
        if not upload_info:
            return False

        total_chunks = upload_info.get("total_chunks", 0)
        chunks_received = upload_info.get("chunks_received", [])

        return len(chunks_received) == total_chunks and all(
            i in chunks_received for i in range(1, total_chunks + 1)
        )

    async def reassemble_file(
        self: ChunkedUploadHandler, upload_id: str
    ) -> bytes | None:
        """Reassemble file from chunks.

        Args:
        ----
            upload_id: Upload session ID.

        Returns:
        -------
            Complete file content as bytes, or None if incomplete.

        """
        file_key = f"chunked_upload:{upload_id}:file"
        file_content = await self.cache_service.get(file_key)
        if file_content:
            if isinstance(file_content, str):
                return file_content.encode()
            return file_content

        upload_info = await self.get_upload_info(upload_id)
        if not upload_info:
            return None

        if not await self.is_upload_complete(upload_id):
            return None

        total_chunks = upload_info.get("total_chunks", 0)
        chunks_received = upload_info.get("chunks_received", [])

        if len(chunks_received) != total_chunks:
            return None

        file_content = bytearray()
        for chunk_number in sorted(chunks_received):
            chunk_data = await self.get_chunk(upload_id, chunk_number)
            if chunk_data is None:
                return None
            file_content.extend(chunk_data)

        assembled = bytes(file_content)
        await self.cache_service.set(file_key, assembled, ttl=self.upload_ttl)
        return assembled

    async def complete_upload(
        self: ChunkedUploadHandler, upload_id: str
    ) -> dict[str, Any] | None:
        """Mark upload as complete and return file data.

        Args:
        ----
            upload_id: Upload session ID.

        Returns:
        -------
            Upload info dictionary, or None if incomplete.

        """
        if not await self.is_upload_complete(upload_id):
            return None

        file_content = await self.reassemble_file(upload_id)
        if file_content is None:
            return None

        upload_info = await self.get_upload_info(upload_id)
        if not upload_info:
            return None

        upload_info["status"] = "completed"
        upload_info["file_size"] = len(file_content)

        key = self._get_upload_key(upload_id)
        await self.cache_service.set(key, json.dumps(upload_info), ttl=self.upload_ttl)

        return upload_info

    async def cleanup_upload(self: ChunkedUploadHandler, upload_id: str) -> None:
        """Clean up upload session and chunks.

        Args:
        ----
            upload_id: Upload session ID.

        """
        upload_info = await self.get_upload_info(upload_id)
        if not upload_info:
            return

        total_chunks = upload_info.get("total_chunks", 0)

        for chunk_number in range(1, total_chunks + 1):
            chunk_key = self._get_chunk_key(upload_id, chunk_number)
            await self.cache_service.delete(chunk_key)

        file_key = f"chunked_upload:{upload_id}:file"
        await self.cache_service.delete(file_key)

        key = self._get_upload_key(upload_id)
        await self.cache_service.delete(key)

        self.logger.info(
            f"Cleaned up upload session: {upload_id}",
            extra={"service": "ChunkedUploadHandler"},
        )


__all__ = ["ChunkedUploadHandler"]
