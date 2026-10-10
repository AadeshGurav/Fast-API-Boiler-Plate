"""File upload routes: single-shot and chunked."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.routes.files.common import get_file_service
from app.models.auth import TokenPayload
from app.models.file import ChunkUploadResponse, FileResponse
from app.services.file import FileService
from app.services.file.chunked_upload import UploadSizeMismatchError
from app.services.file.streams import iter_upload
from app.utils.permissions import get_current_user

router = APIRouter(tags=["File Upload"])


def _parse_tags(tags: str | None) -> list[str]:
    return [t.strip() for t in (tags or "").split(",") if t.strip()]


def _parse_metadata(metadata: str | None) -> dict[str, Any]:
    if not metadata:
        return {}
    try:
        parsed = json.loads(metadata)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="metadata must be valid JSON"
        ) from e
    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="metadata must be a JSON object"
        )
    return parsed


async def _read_limited(upload: UploadFile, limit: int) -> bytes:
    """Read an upload, refusing anything over ``limit`` bytes."""
    content = await upload.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {limit} byte limit",
        )
    return content


@router.post("", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    filename: str | None = Form(None),
    tags: str | None = Form(None),
    metadata: str | None = Form(None),
    user: TokenPayload = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> FileResponse:
    """Upload a single file."""
    try:
        return await file_service.upload_stream(
            user_id=user.user_id,
            filename=filename or file.filename or "uploaded_file",
            chunks=iter_upload(file),
            content_type=file.content_type or "application/octet-stream",
            tags=_parse_tags(tags),
            metadata=_parse_metadata(metadata),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/chunk", response_model=ChunkUploadResponse)
async def upload_chunk(
    chunk: UploadFile = File(...),
    upload_id: str = Form(...),
    chunk_number: int = Form(...),
    total_chunks: int = Form(...),
    total_size: int = Form(...),
    filename: str = Form(...),
    content_type: str | None = Form(None),
    tags: str | None = Form(None),
    metadata: str | None = Form(None),
    user: TokenPayload = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> ChunkUploadResponse:
    """Upload one chunk (1-based) of a larger file; the session starts with the first."""
    handler = file_service.chunked_upload_handler
    data = await _read_limited(chunk, handler.max_chunk_size)
    try:
        await handler.start_upload(
            user_id=user.user_id,
            upload_id=upload_id,
            total_chunks=total_chunks,
            total_size=total_size,
            filename=filename,
            content_type=content_type,
            tags=_parse_tags(tags),
            metadata=_parse_metadata(metadata),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    if not await handler.save_chunk(user.user_id, upload_id, chunk_number, data):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chunk rejected: unknown upload, number out of range, or empty/oversized",
        )

    received = await handler.received_chunks(user.user_id, upload_id)
    return ChunkUploadResponse(
        upload_id=upload_id,
        chunk_number=chunk_number,
        received=True,
        chunks_received=len(received),
        total_chunks=total_chunks,
    )


@router.post("/chunk/complete", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def complete_chunked_upload(
    upload_id: str,
    user: TokenPayload = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> FileResponse:
    """Assemble the staged chunks into a stored file."""
    handler = file_service.chunked_upload_handler
    info = await handler.get_upload_info(user.user_id, upload_id)
    if not info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")

    chunks = await handler.open_assembled(user.user_id, upload_id)
    if chunks is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Upload incomplete")

    try:
        response = await file_service.upload_stream(
            user_id=user.user_id,
            filename=info["filename"],
            chunks=chunks,
            content_type=info["content_type"],
            tags=info.get("tags", []),
            metadata=info.get("metadata", {}),
        )
    except UploadSizeMismatchError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload size does not match what was declared",
        ) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    await handler.cleanup(user.user_id, upload_id)
    return response


__all__ = ["router"]
