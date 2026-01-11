"""File download routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response, StreamingResponse

from app import container as app_container
from app.models.file import FileResponse
from app.services.file import FileService
from app.utils.permissions import get_current_user

router = APIRouter(tags=["File Download"])


@router.get("/{file_id}", response_class=StreamingResponse)
async def download_file(
    file_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(lambda: app_container.file_service()),
) -> StreamingResponse:
    """Download a file.

    Args:
    ----
        file_id: File ID.
        request: FastAPI request object.
        current_user: Current authenticated user.
        file_service: FileService instance.

    Returns:
    -------
        StreamingResponse with file content.

    Raises:
    ------
        HTTPException: If file not found or unauthorized.

    """
    try:
        user_id = (
            current_user.user_id
            if hasattr(current_user, "user_id")
            else current_user.get("user_id")
        )
        result = await file_service.download_file(file_id, user_id=user_id)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        file_content, file_metadata = result

        return StreamingResponse(
            iter([file_content]),
            media_type=file_metadata.content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{file_metadata.filename}"',
                "Content-Length": str(file_metadata.size),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Download failed: {str(e)}",
        ) from e


@router.get("/{file_id}/metadata", response_model=FileResponse)
async def get_file_metadata(
    file_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(lambda: app_container.file_service()),
) -> FileResponse:
    """Get file metadata.

    Args:
    ----
        file_id: File ID.
        request: FastAPI request object.
        current_user: Current authenticated user.
        file_service: FileService instance.

    Returns:
    -------
        FileResponse with file information.

    Raises:
    ------
        HTTPException: If file not found or unauthorized.

    """
    try:
        user_id = (
            current_user.user_id
            if hasattr(current_user, "user_id")
            else current_user.get("user_id")
        )
        file_response = await file_service.get_file_metadata(file_id, user_id=user_id)

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
            detail=f"Failed to get metadata: {str(e)}",
        ) from e


__all__ = ["router"]

