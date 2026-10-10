"""Helpers for moving file bytes around as async iterators instead of whole ``bytes``."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from app.core.interfaces.storage_interface import STREAM_CHUNK_SIZE


async def iter_bytes(content: bytes, chunk_size: int = STREAM_CHUNK_SIZE) -> AsyncIterator[bytes]:
    """``content`` as an async iterator of pieces."""
    for start in range(0, len(content), chunk_size):
        yield content[start : start + chunk_size]


async def iter_upload(upload, chunk_size: int = STREAM_CHUNK_SIZE) -> AsyncIterator[bytes]:
    """The pieces of a Starlette ``UploadFile`` (spooled to disk past 1 MiB, so this never
    holds the whole file in memory)."""
    while piece := await upload.read(chunk_size):
        yield piece


class MeteredStream:
    """Pass-through over ``chunks`` that counts and SHA-256-hashes what flows by, and
    refuses to deliver more than ``limit`` bytes."""

    def __init__(self, chunks: AsyncIterator[bytes], limit: int) -> None:
        self._chunks = chunks
        self._limit = limit
        self._sha256 = hashlib.sha256()
        self.size = 0

    async def __aiter__(self) -> AsyncIterator[bytes]:
        async for chunk in self._chunks:
            self.size += len(chunk)
            if self.size > self._limit:
                raise ValueError(f"File size exceeds maximum of {self._limit} bytes")
            self._sha256.update(chunk)
            yield chunk

    async def drain(self) -> None:
        """Consume the stream (to learn its size and hash)."""
        async for _ in self:
            pass

    @property
    def hexdigest(self) -> str:
        """SHA-256 of everything delivered so far."""
        return self._sha256.hexdigest()


__all__ = ["MeteredStream", "iter_bytes", "iter_upload"]
