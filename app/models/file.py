"""File models for upload and management."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class FileMetadata(BaseModel):
    """File metadata model for database storage."""

    file_id: str = Field(..., description="Unique file identifier")
    user_id: str = Field(..., description="User who uploaded the file")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type")
    size: int = Field(..., description="File size in bytes")
    hash: str = Field(..., description="SHA256 hash of file content")
    version: int = Field(default=1, description="File version number")
    storage_path: str = Field(..., description="Storage path relative to base")
    storage_backend: str = Field(default="local", description="Storage backend type")
    tags: list[str] = Field(default_factory=list, description="File tags")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    thumbnail_paths: dict[str, str] = Field(
        default_factory=dict, description="Thumbnail paths by size"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last update timestamp"
    )
    deleted_at: datetime | None = Field(default=None, description="Soft delete timestamp")


class FileResponse(BaseModel):
    """Response model for file information."""

    file_id: str = Field(..., description="Unique file identifier")
    user_id: str = Field(..., description="User who uploaded the file")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type")
    size: int = Field(..., description="File size in bytes")
    version: int = Field(..., description="File version number")
    tags: list[str] = Field(..., description="File tags")
    metadata: dict[str, Any] = Field(..., description="Additional metadata")
    thumbnail_urls: dict[str, str] = Field(
        default_factory=dict, description="Thumbnail URLs by size"
    )
    download_url: str = Field(..., description="File download URL")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class ChunkUploadResponse(BaseModel):
    """Response model for chunk upload."""

    upload_id: str = Field(..., description="Upload session ID")
    chunk_number: int = Field(..., description="Chunk number received")
    received: bool = Field(..., description="Whether chunk was received")
    chunks_received: int = Field(..., description="Total chunks received so far")
    total_chunks: int = Field(..., description="Total chunks expected")


class FileListResponse(BaseModel):
    """Response model for file listing."""

    files: list[FileResponse] = Field(..., description="List of files")
    total: int = Field(..., description="Total number of files")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    has_next: bool = Field(..., description="Whether there are more pages")
    next_cursor: str | None = Field(None, description="Pass as ?cursor= for the next page")


class FileUpdateRequest(BaseModel):
    """Request model for updating file metadata."""

    filename: str | None = Field(None, min_length=1, max_length=255, description="Updated filename")
    tags: list[str] | None = Field(None, description="Updated tags")
    metadata: dict[str, Any] | None = Field(None, description="Updated metadata")


class SpreadsheetData(BaseModel):
    """Response model for spreadsheet data."""

    sheets: dict[str, list[list[Any]]] = Field(
        ..., description="Dictionary mapping sheet names to data (list of lists)"
    )
    headers: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Optional headers per sheet",
    )


class SpreadsheetInfo(BaseModel):
    """Workbook/sheet metadata."""

    sheet_names: list[str] = Field(..., description="List of sheet names")
    sheet_info: dict[str, dict[str, int]] = Field(..., description="Row/column counts per sheet")
    format: str = Field(..., description="File format (xlsx, ods, csv)")
    total_sheets: int = Field(..., description="Total number of sheets")


class SpreadsheetCreateRequest(BaseModel):
    """Request model for creating spreadsheets."""

    data: dict[str, list[list[Any]]] = Field(
        ..., description="Dictionary mapping sheet names to data (list of lists)"
    )
    format: str = Field(default="xlsx", description="Output format (xlsx, ods, csv)")
    headers: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Optional headers per sheet",
    )


class SpreadsheetUpdateRequest(BaseModel):
    """Request model for updating spreadsheets."""

    data: dict[str, list[list[Any]]] = Field(
        ..., description="Dictionary mapping sheet names to data (list of lists)"
    )
    sheet_name: str | None = Field(None, description="Optional specific sheet to update")


class SpreadsheetReadResponse(BaseModel):
    """Response model for read operations."""

    data: SpreadsheetData = Field(..., description="Spreadsheet data")
    info: SpreadsheetInfo = Field(..., description="Workbook metadata")


__all__ = [
    "ChunkUploadResponse",
    "FileListResponse",
    "FileMetadata",
    "FileResponse",
    "FileUpdateRequest",
    "SpreadsheetCreateRequest",
    "SpreadsheetData",
    "SpreadsheetInfo",
    "SpreadsheetReadResponse",
    "SpreadsheetUpdateRequest",
]
