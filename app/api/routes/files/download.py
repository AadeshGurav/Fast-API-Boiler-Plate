"""File download routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.api.routes.files.common import get_file_service, not_found, serve_stored_file
from app.models.auth import TokenPayload
from app.models.file import FileResponse
from app.services.file import FileService
from app.utils.permissions import get_current_user

router = APIRouter(tags=["File Download"])


@router.get("/{file_id}", response_class=Response)
async def download_file(
    file_id: str,
    version: int | None = Query(None, ge=1, description="Version (default: newest)"),
    user: TokenPayload = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> Response:
    """Download a file as an attachment."""
    record = await file_service.get_owned(file_id, user.user_id, version=version)
    if record is None:
        raise not_found()
    return await serve_stored_file(file_service, record["storage_path"], record)


@router.get("/{file_id}/thumbnails/{size}", response_class=Response)
async def download_thumbnail(
    file_id: str,
    size: str,
    version: int | None = Query(None, ge=1, description="Version (default: newest)"),
    user: TokenPayload = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> Response:
    """A generated thumbnail of an image file (sizes are listed in ``thumbnail_urls``)."""
    record = await file_service.get_owned(file_id, user.user_id, version=version)
    thumbnail_path = (record or {}).get("thumbnail_paths", {}).get(size)
    if record is None or thumbnail_path is None:
        raise not_found()
    return await serve_stored_file(file_service, thumbnail_path, record)


@router.get("/{file_id}/metadata", response_model=FileResponse)
async def get_file_metadata(
    file_id: str,
    user: TokenPayload = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> FileResponse:
    """Metadata of the newest version of one of the caller's files."""
    response = await file_service.get_file_metadata(file_id, user.user_id)
    if not response:
        raise not_found()
    return response


__all__ = ["router"]
