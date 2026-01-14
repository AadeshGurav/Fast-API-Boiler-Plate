"""Spreadsheet processing routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from app import container as app_container
from app.models.file import (
    FileResponse,
    SpreadsheetCreateRequest,
    SpreadsheetInfo,
    SpreadsheetReadResponse,
    SpreadsheetUpdateRequest,
)
from app.services.file import FileService
from app.utils.permissions import get_current_user

router = APIRouter(tags=["Spreadsheet Operations"])


@router.get("/{file_id}/spreadsheet/read", response_model=SpreadsheetReadResponse)
async def read_spreadsheet(
    file_id: str,
    request: Request,
    sheet_name: str | None = Query(None, description="Optional specific sheet to read"),
    format: str = Query("json", description="Response format (json or csv)"),
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(lambda: app_container.file_service()),
) -> SpreadsheetReadResponse:
    """Read spreadsheet data.

    Args:
    ----
        file_id: File ID.
        request: FastAPI request object.
        sheet_name: Optional specific sheet to read.
        format: Response format (json or csv).
        current_user: Current authenticated user.
        file_service: FileService instance.

    Returns:
    -------
        SpreadsheetReadResponse with data and info.

    Raises:
    ------
        HTTPException: If read fails.

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

        file_metadata = await file_service.get_file_metadata(file_id, user_id)
        if not file_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        if not file_service.spreadsheet_processor:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Spreadsheet processing not available",
            )

        if not file_service.spreadsheet_processor._is_spreadsheet_type(
            file_metadata.content_type
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is not a spreadsheet",
            )

        data = await file_service.spreadsheet_processor.read_spreadsheet(
            file_metadata.storage_path, sheet_name
        )

        info = await file_service.spreadsheet_processor.get_sheet_info(
            file_metadata.storage_path
        )

        from app.models.file import SpreadsheetData, SpreadsheetInfo

        spreadsheet_data = SpreadsheetData(sheets=data, headers={})
        spreadsheet_info = SpreadsheetInfo(
            sheet_names=info.get("sheet_names", []),
            sheet_info=info.get("sheet_info", {}),
            format=info.get("format", ""),
            total_sheets=info.get("total_sheets", 0),
        )

        return SpreadsheetReadResponse(data=spreadsheet_data, info=spreadsheet_info)

    except HTTPException:
        raise
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read spreadsheet: {str(e)}",
        ) from e


@router.get("/{file_id}/spreadsheet/info", response_model=SpreadsheetInfo)
async def get_spreadsheet_info(
    file_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(lambda: app_container.file_service()),
) -> SpreadsheetInfo:
    """Get workbook/sheet metadata.

    Args:
    ----
        file_id: File ID.
        request: FastAPI request object.
        current_user: Current authenticated user.
        file_service: FileService instance.

    Returns:
    -------
        SpreadsheetInfo with workbook metadata.

    Raises:
    ------
        HTTPException: If info retrieval fails.

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

        file_metadata = await file_service.get_file_metadata(file_id, user_id)
        if not file_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        if not file_service.spreadsheet_processor:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Spreadsheet processing not available",
            )

        if not file_service.spreadsheet_processor._is_spreadsheet_type(
            file_metadata.content_type
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is not a spreadsheet",
            )

        info = await file_service.spreadsheet_processor.get_sheet_info(
            file_metadata.storage_path
        )

        return SpreadsheetInfo(
            sheet_names=info.get("sheet_names", []),
            sheet_info=info.get("sheet_info", {}),
            format=info.get("format", ""),
            total_sheets=info.get("total_sheets", 0),
        )

    except HTTPException:
        raise
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get spreadsheet info: {str(e)}",
        ) from e


@router.put("/{file_id}/spreadsheet/update")
async def update_spreadsheet(
    file_id: str,
    update_request: SpreadsheetUpdateRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(lambda: app_container.file_service()),
) -> JSONResponse:
    """Update existing spreadsheet.

    Args:
    ----
        file_id: File ID.
        update_request: Update request with spreadsheet data.
        request: FastAPI request object.
        current_user: Current authenticated user.
        file_service: FileService instance.

    Returns:
    -------
        JSONResponse with success status.

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

        file_metadata = await file_service.get_file_metadata(file_id, user_id)
        if not file_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        if not file_service.spreadsheet_processor:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Spreadsheet processing not available",
            )

        if not file_service.spreadsheet_processor._is_spreadsheet_type(
            file_metadata.content_type
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is not a spreadsheet",
            )

        success = await file_service.spreadsheet_processor.update_spreadsheet(
            file_metadata.storage_path,
            update_request.data,
            update_request.sheet_name,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update spreadsheet",
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Spreadsheet updated successfully"},
        )

    except HTTPException:
        raise
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update spreadsheet: {str(e)}",
        ) from e


@router.delete("/{file_id}/spreadsheet/sheet/{sheet_name}")
async def delete_sheet(
    file_id: str,
    sheet_name: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(lambda: app_container.file_service()),
) -> JSONResponse:
    """Delete a sheet from workbook.

    Args:
    ----
        file_id: File ID.
        sheet_name: Name of sheet to delete.
        request: FastAPI request object.
        current_user: Current authenticated user.
        file_service: FileService instance.

    Returns:
    -------
        JSONResponse with success status.

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

        file_metadata = await file_service.get_file_metadata(file_id, user_id)
        if not file_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        if not file_service.spreadsheet_processor:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Spreadsheet processing not available",
            )

        if not file_service.spreadsheet_processor._is_spreadsheet_type(
            file_metadata.content_type
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is not a spreadsheet",
            )

        success = await file_service.spreadsheet_processor.delete_sheet(
            file_metadata.storage_path, sheet_name
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete sheet",
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": f"Sheet '{sheet_name}' deleted successfully"},
        )

    except HTTPException:
        raise
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete sheet: {str(e)}",
        ) from e


@router.post("/spreadsheet/create", response_model=FileResponse)
async def create_spreadsheet_file(
    create_request: SpreadsheetCreateRequest,
    request: Request,
    filename: str = Query(..., description="Filename for the new spreadsheet"),
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(lambda: app_container.file_service()),
) -> FileResponse:
    """Create new spreadsheet file.

    Args:
    ----
        create_request: Create request with spreadsheet data.
        request: FastAPI request object.
        filename: Filename for the new spreadsheet.
        current_user: Current authenticated user.
        file_service: FileService instance.

    Returns:
    -------
        FileResponse with file information.

    Raises:
    ------
        HTTPException: If creation fails.

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

        if not file_service.spreadsheet_processor:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Spreadsheet processing not available",
            )

        file_ext = f".{create_request.format}"
        if not filename.endswith(file_ext):
            filename = f"{filename}{file_ext}"

        mime_type_map = {
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "ods": "application/vnd.oasis.opendocument.spreadsheet",
            "csv": "text/csv",
        }
        content_type = mime_type_map.get(
            create_request.format, "application/octet-stream"
        )

        file_id = str(uuid.uuid4())
        storage_path = file_service._generate_storage_path(
            user_id, file_id, 1, filename
        )

        success = await file_service.spreadsheet_processor.create_spreadsheet(
            storage_path,
            create_request.data,
            create_request.format,
            create_request.headers,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create spreadsheet",
            )

        content = await file_service.storage_backend.read(storage_path)
        if not content:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to read created spreadsheet",
            )

        return await file_service.upload_file(
            user_id,
            filename,
            content,
            content_type,
            metadata={"created_via": "spreadsheet_api"},
        )

    except HTTPException:
        raise
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create spreadsheet: {str(e)}",
        ) from e


__all__ = ["router"]
