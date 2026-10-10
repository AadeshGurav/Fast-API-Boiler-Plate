"""Spreadsheet routes: read, create, and edit spreadsheet files.

Edits never modify stored bytes in place; each one produces a new file version.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.routes.files.common import get_file_service, not_found
from app.models.auth import TokenPayload
from app.models.file import (
    FileResponse,
    SpreadsheetCreateRequest,
    SpreadsheetData,
    SpreadsheetInfo,
    SpreadsheetReadResponse,
    SpreadsheetUpdateRequest,
)
from app.services.file import FileService
from app.utils.permissions import get_current_user

router = APIRouter(tags=["Spreadsheet Operations"])

MIME_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ods": "application/vnd.oasis.opendocument.spreadsheet",
    "csv": "text/csv",
}


def _bad_request(error: ValueError) -> HTTPException:
    """Processor errors are about the caller's data (unknown sheet, bad name, too big)."""
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


def _processor(file_service: FileService) -> Any:
    if not file_service.spreadsheet_processor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Spreadsheet processing not available",
        )
    return file_service.spreadsheet_processor


async def _owned_spreadsheet(
    file_id: str, user: TokenPayload, file_service: FileService
) -> dict[str, Any]:
    """The caller's newest version of ``file_id``, which must be a spreadsheet."""
    latest = await file_service.get_owned(file_id, user.user_id)
    if not latest:
        raise not_found()
    if not _processor(file_service)._is_spreadsheet_type(latest["content_type"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File is not a spreadsheet"
        )
    return latest


def _info(raw: dict[str, Any]) -> SpreadsheetInfo:
    return SpreadsheetInfo(
        sheet_names=raw.get("sheet_names", []),
        sheet_info=raw.get("sheet_info", {}),
        format=raw.get("format", ""),
        total_sheets=raw.get("total_sheets", 0),
    )


@router.get("/{file_id}/spreadsheet/read", response_model=SpreadsheetReadResponse)
async def read_spreadsheet(
    file_id: str,
    sheet_name: str | None = Query(None, description="Only this sheet"),
    user: TokenPayload = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> SpreadsheetReadResponse:
    """Cell data and workbook info of the newest version."""
    latest = await _owned_spreadsheet(file_id, user, file_service)
    processor = _processor(file_service)
    try:
        data = await processor.read_spreadsheet(latest["storage_path"], sheet_name)
        info = await processor.get_sheet_info(latest["storage_path"])
    except ValueError as e:
        raise _bad_request(e) from e
    return SpreadsheetReadResponse(data=SpreadsheetData(sheets=data, headers={}), info=_info(info))


@router.get("/{file_id}/spreadsheet/info", response_model=SpreadsheetInfo)
async def get_spreadsheet_info(
    file_id: str,
    user: TokenPayload = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> SpreadsheetInfo:
    """Sheet names and sizes of the newest version."""
    latest = await _owned_spreadsheet(file_id, user, file_service)
    try:
        return _info(await _processor(file_service).get_sheet_info(latest["storage_path"]))
    except ValueError as e:
        raise _bad_request(e) from e


@router.put("/{file_id}/spreadsheet/update", response_model=FileResponse)
async def update_spreadsheet(
    file_id: str,
    update_request: SpreadsheetUpdateRequest,
    user: TokenPayload = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> FileResponse:
    """Write cell data; returns the new version."""
    await _owned_spreadsheet(file_id, user, file_service)
    processor = _processor(file_service)

    try:
        response = await file_service.modify_as_new_version(
            file_id,
            user.user_id,
            lambda path: processor.update_spreadsheet(
                path, update_request.data, update_request.sheet_name
            ),
        )
    except ValueError as e:
        raise _bad_request(e) from e
    if response is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update spreadsheet"
        )
    return response


@router.delete("/{file_id}/spreadsheet/sheet/{sheet_name}", response_model=FileResponse)
async def delete_sheet(
    file_id: str,
    sheet_name: str,
    user: TokenPayload = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> FileResponse:
    """Remove a sheet; returns the new version."""
    await _owned_spreadsheet(file_id, user, file_service)
    processor = _processor(file_service)

    try:
        response = await file_service.modify_as_new_version(
            file_id, user.user_id, lambda path: processor.delete_sheet(path, sheet_name)
        )
    except ValueError as e:
        raise _bad_request(e) from e
    if response is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete sheet"
        )
    return response


@router.post(
    "/spreadsheet/create", response_model=FileResponse, status_code=status.HTTP_201_CREATED
)
async def create_spreadsheet_file(
    create_request: SpreadsheetCreateRequest,
    filename: str = Query("spreadsheet", min_length=1, max_length=200),
    user: TokenPayload = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> FileResponse:
    """Create a new spreadsheet file from cell data."""
    processor = _processor(file_service)
    if create_request.format not in MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"format must be one of {sorted(MIME_TYPES)}",
        )

    extension = f".{create_request.format}"
    if not filename.endswith(extension):
        filename += extension

    # Build in a scratch location, then store through the normal upload path so the
    # file gets proper ids, hashing and validation.
    scratch = f"_tmp/{user.user_id}/{uuid.uuid4().hex}{extension}"
    try:
        if not await processor.create_spreadsheet(
            scratch, create_request.data, create_request.format, create_request.headers
        ):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create spreadsheet",
            )
        content = await file_service.storage_backend.read(scratch)
    except ValueError as e:
        raise _bad_request(e) from e
    finally:
        await file_service.storage_backend.delete(scratch)

    if not content:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create spreadsheet"
        )

    try:
        return await file_service.upload_file(
            user.user_id,
            filename,
            content,
            MIME_TYPES[create_request.format],
            metadata={"created_via": "spreadsheet_api"},
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


__all__ = ["router"]
