"""File management routes: listing, metadata updates, versions, deletion."""

from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)

from app.api.routes.files.common import get_file_service, not_found
from app.api.routes.files.upload import _parse_metadata, _parse_tags
from app.models.auth import TokenPayload
from app.models.file import FileListResponse, FileResponse, FileUpdateRequest
from app.services.data.cursor import InvalidCursorError
from app.services.file import FileService
from app.services.file.streams import iter_upload
from app.utils.permissions import get_current_user

router = APIRouter(tags=["File Management"])


@router.get("/", response_model=FileListResponse)
async def list_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    tags: str | None = Query(None, description="Comma-separated; matches any"),
    cursor: str | None = Query(
        None, max_length=512, description="next_cursor from the previous page; replaces page"
    ),
    user: TokenPayload = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> FileListResponse:
    """The caller's files, newest first. Page with ``page``, or follow ``next_cursor``, which
    stays fast at any depth and never repeats or skips a file when others are added."""
    try:
        files, total, next_cursor = await file_service.list_files(
            user.user_id,
            limit=page_size,
            offset=(page - 1) * page_size,
            tags=_parse_tags(tags) or None,
            cursor=cursor,
        )
    except InvalidCursorError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return FileListResponse(
        files=files,
        total=total,
        page=page,
        page_size=page_size,
        has_next=next_cursor is not None,
        next_cursor=next_cursor,
    )


@router.put("/{file_id}", response_model=FileResponse)
async def update_file(
    file_id: str,
    update_request: FileUpdateRequest,
    user: TokenPayload = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> FileResponse:
    """Change a file's name, tags or metadata."""
    response = await file_service.update_file_metadata(
        file_id=file_id,
        user_id=user.user_id,
        filename=update_request.filename,
        tags=update_request.tags,
        metadata=update_request.metadata,
    )
    if not response:
        raise not_found()
    return response


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    hard_delete: bool = Query(False, description="Also remove the stored bytes"),
    user: TokenPayload = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> dict[str, str]:
    """Delete a file (soft by default)."""
    if not await file_service.delete_file(file_id, user.user_id, hard_delete=hard_delete):
        raise not_found()
    return {"message": "File deleted successfully", "file_id": file_id}


@router.get("/{file_id}/versions", response_model=list[FileResponse])
async def get_file_versions(
    file_id: str,
    user: TokenPayload = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> list[FileResponse]:
    """All versions of one of the caller's files, newest first."""
    versions = await file_service.get_file_versions(file_id, user.user_id)
    if not versions:
        raise not_found()
    return versions


@router.post(
    "/{file_id}/versions", response_model=FileResponse, status_code=status.HTTP_201_CREATED
)
async def upload_new_version(
    file_id: str,
    file: UploadFile = File(...),
    filename: str | None = Form(None),
    tags: str | None = Form(None),
    metadata: str | None = Form(None),
    user: TokenPayload = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> FileResponse:
    """Upload a new version of one of the caller's files."""
    try:
        return await file_service.upload_stream(
            user.user_id,
            filename or file.filename or "uploaded_file",
            iter_upload(file),
            file.content_type or "application/octet-stream",
            tags=_parse_tags(tags),
            metadata=_parse_metadata(metadata),
            file_id=file_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


__all__ = ["router"]
