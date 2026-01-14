"""File upload routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, status

from app import container as app_container
from app.models.file import ChunkUploadResponse, FileResponse
from app.services.file import FileService
from app.utils.permissions import get_current_user

router = APIRouter(tags=["File Upload"])


@router.post("", response_model=FileResponse)
async def upload_file(
    request: Request,
    file: bytes = File(...),
    filename: str = Form(None),
    content_type: str = Form(None),
    tags: str = Form(None),
    metadata: str = Form(None),
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(lambda: app_container.file_service()),
) -> FileResponse:
    """Upload a single file.

    Args:
    ----
        request: FastAPI request object.
        file: File content as bytes.
        filename: Optional filename override.
        content_type: Optional content type.
        tags: Optional comma-separated tags.
        metadata: Optional JSON metadata string.
        current_user: Current authenticated user.
        file_service: FileService instance.

    Returns:
    -------
        FileResponse with file information.

    Raises:
    ------
        HTTPException: If upload fails.

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

        content_type = content_type or request.headers.get(
            "content-type", "application/octet-stream"
        )

        tag_list = []
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]

        metadata_dict = {}
        if metadata:
            import json

            try:
                metadata_dict = json.loads(metadata)
            except json.JSONDecodeError:
                pass

        file_response = await file_service.upload_file(
            user_id=user_id,
            filename=filename or "uploaded_file",
            content=file,
            content_type=content_type,
            tags=tag_list,
            metadata=metadata_dict,
        )

        return file_response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}",
        ) from e


@router.post("/chunk", response_model=ChunkUploadResponse)
async def upload_chunk(
    request: Request,
    chunk: bytes = File(...),
    upload_id: str = Form(...),
    chunk_number: int = Form(...),
    total_chunks: int = Form(...),
    chunk_size: int = Form(...),
    total_size: int = Form(...),
    filename: str = Form(...),
    content_type: str = Form(None),
    tags: str = Form(None),
    metadata: str = Form(None),
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(lambda: app_container.file_service()),
) -> ChunkUploadResponse:
    """Upload a chunk of a file.

    Args:
    ----
        request: FastAPI request object.
        chunk: Chunk content as bytes.
        upload_id: Upload session ID.
        chunk_number: Chunk sequence number.
        total_chunks: Total number of chunks.
        chunk_size: Size of this chunk.
        total_size: Total file size.
        filename: Original filename.
        content_type: Optional content type.
        tags: Optional comma-separated tags.
        metadata: Optional JSON metadata string.
        current_user: Current authenticated user.
        file_service: FileService instance.

    Returns:
    -------
        ChunkUploadResponse with upload status.

    Raises:
    ------
        HTTPException: If chunk upload fails.

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

        if not file_service.chunked_upload_handler:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Chunked upload not available",
            )

        upload_info = await file_service.chunked_upload_handler.get_upload_info(
            upload_id
        )
        if not upload_info:
            await file_service.chunked_upload_handler.start_upload(
                upload_id=upload_id,
                total_chunks=total_chunks,
                total_size=total_size,
                filename=filename,
                content_type=content_type,
                user_id=user_id,
            )

        saved = await file_service.chunked_upload_handler.save_chunk(
            upload_id=upload_id, chunk_number=chunk_number, chunk_data=chunk
        )

        if not saved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to save chunk"
            )

        upload_info = await file_service.chunked_upload_handler.get_upload_info(
            upload_id
        )
        chunks_received = (
            len(upload_info.get("chunks_received", [])) if upload_info else 0
        )

        return ChunkUploadResponse(
            upload_id=upload_id,
            chunk_number=chunk_number,
            received=saved,
            chunks_received=chunks_received,
            total_chunks=total_chunks,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chunk upload failed: {str(e)}",
        ) from e


@router.post("/chunk/complete", response_model=FileResponse)
async def complete_chunked_upload(
    upload_id: str,
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(lambda: app_container.file_service()),
) -> FileResponse:
    """Complete a chunked upload and create file.

    Args:
    ----
        upload_id: Upload session ID.
        current_user: Current authenticated user.
        file_service: FileService instance.

    Returns:
    -------
        FileResponse with file information.

    Raises:
    ------
        HTTPException: If completion fails.

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

        if not file_service.chunked_upload_handler:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Chunked upload not available",
            )

        upload_info = await file_service.chunked_upload_handler.complete_upload(
            upload_id
        )
        if not upload_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upload not complete or not found",
            )

        if upload_info.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized"
            )

        file_content = await file_service.chunked_upload_handler.reassemble_file(
            upload_id
        )
        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="File content not found"
            )

        file_response = await file_service.upload_file(
            user_id=user_id,
            filename=upload_info.get("filename", "uploaded_file"),
            content=file_content,
            content_type=upload_info.get("content_type", "application/octet-stream"),
            tags=upload_info.get("tags", []),
            metadata=upload_info.get("metadata", {}),
        )

        await file_service.chunked_upload_handler.cleanup_upload(upload_id)

        return file_response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete upload: {str(e)}",
        ) from e


__all__ = ["router"]
