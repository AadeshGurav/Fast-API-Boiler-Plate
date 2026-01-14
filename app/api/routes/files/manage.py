"""File management routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from app import container as app_container
from app.models.file import FileListResponse, FileResponse, FileUpdateRequest
from app.services.file import FileService
from app.utils.permissions import get_current_user

router = APIRouter(tags=["File Management"])


@router.get("/", response_model=FileListResponse)
async def list_files(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    tags: str = Query(None),
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(lambda: app_container.file_service()),
) -> FileListResponse:
    """List files for the current user.

    Args:
    ----
        request: FastAPI request object.
        page: Page number (1-indexed).
        page_size: Number of files per page.
        tags: Optional comma-separated tags filter.
        current_user: Current authenticated user.
        file_service: FileService instance.

    Returns:
    -------
        FileListResponse with files and pagination info.

    """
    try:
        user_id = (
            current_user.user_id
            if hasattr(current_user, "user_id")
            else current_user.get("user_id")
        )
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated",
            )

        offset = (page - 1) * page_size

        tag_list = None
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]

        files = await file_service.list_files(
            user_id, limit=page_size, offset=offset, tags=tag_list
        )

        return FileListResponse(
            files=files,
            total=len(files),
            page=page,
            page_size=page_size,
            has_next=len(files) == page_size,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}",
        ) from e


@router.put("/{file_id}", response_model=FileResponse)
async def update_file(
    file_id: str,
    update_request: FileUpdateRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(lambda: app_container.file_service()),
) -> FileResponse:
    """Update file metadata.

    Args:
    ----
        file_id: File ID.
        update_request: Update request with new metadata.
        request: FastAPI request object.
        current_user: Current authenticated user.
        file_service: FileService instance.

    Returns:
    -------
        Updated FileResponse.

    Raises:
    ------
        HTTPException: If update fails.

    """
    try:
        user_id = (
            current_user.user_id
            if hasattr(current_user, "user_id")
            else current_user.get("user_id")
        )
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated",
            )

        file_response = await file_service.update_file_metadata(
            file_id=file_id,
            user_id=user_id,
            filename=update_request.filename,
            tags=update_request.tags,
            metadata=update_request.metadata,
        )

        if not file_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        return file_response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update file: {str(e)}",
        ) from e


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    request: Request,
    hard_delete: bool = Query(False),
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(lambda: app_container.file_service()),
) -> JSONResponse:
    """Delete a file.

    Args:
    ----
        file_id: File ID.
        request: FastAPI request object.
        hard_delete: Whether to permanently delete.
        current_user: Current authenticated user.
        file_service: FileService instance.

    Returns:
    -------
        JSONResponse with success message.

    Raises:
    ------
        HTTPException: If deletion fails.

    """
    try:
        user_id = (
            current_user.user_id
            if hasattr(current_user, "user_id")
            else current_user.get("user_id")
        )
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated",
            )

        success = await file_service.delete_file(
            file_id, user_id, hard_delete=hard_delete
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        return JSONResponse(
            content={"message": "File deleted successfully", "file_id": file_id}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}",
        ) from e


@router.get("/{file_id}/versions", response_model=list[FileResponse])
async def get_file_versions(
    file_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(lambda: app_container.file_service()),
) -> list[FileResponse]:
    """Get all versions of a file.

    Args:
    ----
        file_id: File ID.
        request: FastAPI request object.
        current_user: Current authenticated user.
        file_service: FileService instance.

    Returns:
    -------
        List of FileResponse objects for each version.

    Raises:
    ------
        HTTPException: If file not found.

    """
    try:
        user_id = (
            current_user.user_id
            if hasattr(current_user, "user_id")
            else current_user.get("user_id")
        )
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated",
            )

        versions = await file_service.get_file_versions(file_id)

        if not versions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        return versions

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get versions: {str(e)}",
        ) from e


__all__ = ["router"]
