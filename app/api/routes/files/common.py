"""Helpers shared by the file routes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from fastapi import HTTPException, status
from fastapi.responses import RedirectResponse, Response, StreamingResponse

from app.api.deps import get_file_service

if TYPE_CHECKING:
    from app.services.file import FileService


def not_found() -> HTTPException:
    """404 used for missing files and for files owned by someone else alike."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")


def content_disposition(filename: str) -> str:
    """An attachment header that cannot be broken out of by quotes or newlines.

    Always ``attachment``: user-uploaded content must never be rendered inline from our
    origin. The RFC 5987 ``filename*`` carries the real (UTF-8) name; the plain
    ``filename`` is an ASCII-only fallback.
    """
    fallback = "".join(
        c if c.isascii() and c.isprintable() and c not in '"\\/;' else "_" for c in filename
    )
    return f"attachment; filename=\"{fallback or 'download'}\"; filename*=UTF-8''{quote(filename)}"


async def serve_stored_file(
    file_service: FileService, storage_path: str, record: dict[str, Any]
) -> Response:
    """Send a stored object to its owner (access was already checked by the caller).

    With ``file_download_redirect`` and a backend that can sign URLs the client is sent
    straight to the store; otherwise the bytes are streamed through, never buffered.
    """
    disposition = content_disposition(record["filename"])
    storage = file_service.storage_backend
    if file_service.download_redirect:
        url = await storage.download_url(
            storage_path,
            content_type=record["content_type"],
            content_disposition=disposition,
            expires_in=file_service.download_url_ttl,
        )
        if url:
            return RedirectResponse(url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    stream = await storage.open_stream(storage_path)
    if stream is None:
        raise not_found()
    headers = {"Content-Disposition": disposition, "Cache-Control": "private, no-store"}
    if storage_path == record["storage_path"]:  # thumbnails have a different length
        headers["Content-Length"] = str(record["size"])
    return StreamingResponse(stream, media_type=record["content_type"], headers=headers)


__all__ = ["content_disposition", "get_file_service", "not_found", "serve_stored_file"]
