"""File models for upload and management."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.core.dynamic_config import DynamicConfig


class FileMetadata(DynamicConfig):
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
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    thumbnail_paths: dict[str, str] = Field(
        default_factory=dict, description="Thumbnail paths by size"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )
    deleted_at: datetime | None = Field(
        default=None, description="Soft delete timestamp"
    )


class FileUploadRequest(DynamicConfig):
    """Request model for file upload."""

    filename: str | None = Field(None, description="Optional filename override")
    tags: list[str] = Field(default_factory=list, description="File tags")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class FileResponse(DynamicConfig):
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


class ChunkUploadRequest(DynamicConfig):
    """Request model for chunked upload."""

    upload_id: str = Field(..., description="Unique upload session ID")
    chunk_number: int = Field(..., description="Chunk sequence number")
    total_chunks: int = Field(..., description="Total number of chunks")
    chunk_size: int = Field(..., description="Size of this chunk in bytes")
    total_size: int = Field(..., description="Total file size in bytes")
    filename: str = Field(..., description="Original filename")
    content_type: str | None = Field(None, description="MIME type")
    tags: list[str] = Field(default_factory=list, description="File tags")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ChunkUploadResponse(DynamicConfig):
    """Response model for chunk upload."""

    upload_id: str = Field(..., description="Upload session ID")
    chunk_number: int = Field(..., description="Chunk number received")
    received: bool = Field(..., description="Whether chunk was received")
    chunks_received: int = Field(..., description="Total chunks received so far")
    total_chunks: int = Field(..., description="Total chunks expected")


class FileListResponse(DynamicConfig):
    """Response model for file listing."""

    files: list[FileResponse] = Field(..., description="List of files")
    total: int = Field(..., description="Total number of files")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    has_next: bool = Field(..., description="Whether there are more pages")


class FileUpdateRequest(DynamicConfig):
    """Request model for updating file metadata."""

    filename: str | None = Field(None, description="Updated filename")
    tags: list[str] | None = Field(None, description="Updated tags")
    metadata: dict[str, Any] | None = Field(None, description="Updated metadata")


class FileVersionInfo(DynamicConfig):
    """Information about a file version."""

    version: int = Field(..., description="Version number")
    size: int = Field(..., description="File size in bytes")
    created_at: datetime = Field(..., description="Creation timestamp")
    storage_path: str = Field(..., description="Storage path")


class SpreadsheetData(DynamicConfig):
    """Response model for spreadsheet data."""

    sheets: dict[str, list[list[Any]]] = Field(
        ..., description="Dictionary mapping sheet names to data (list of lists)"
    )
    headers: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Optional headers per sheet",
    )


class SpreadsheetInfo(DynamicConfig):
    """Workbook/sheet metadata."""

    sheet_names: list[str] = Field(..., description="List of sheet names")
    sheet_info: dict[str, dict[str, int]] = Field(
        ..., description="Row/column counts per sheet"
    )
    format: str = Field(..., description="File format (xlsx, ods, csv)")
    total_sheets: int = Field(..., description="Total number of sheets")


class SpreadsheetCreateRequest(DynamicConfig):
    """Request model for creating spreadsheets."""

    data: dict[str, list[list[Any]]] = Field(
        ..., description="Dictionary mapping sheet names to data (list of lists)"
    )
    format: str = Field(default="xlsx", description="Output format (xlsx, ods, csv)")
    headers: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Optional headers per sheet",
    )


class SpreadsheetUpdateRequest(DynamicConfig):
    """Request model for updating spreadsheets."""

    data: dict[str, list[list[Any]]] = Field(
        ..., description="Dictionary mapping sheet names to data (list of lists)"
    )
    sheet_name: str | None = Field(
        None, description="Optional specific sheet to update"
    )


class SpreadsheetReadResponse(DynamicConfig):
    """Response model for read operations."""

    data: SpreadsheetData = Field(..., description="Spreadsheet data")
    info: SpreadsheetInfo = Field(..., description="Workbook metadata")


__all__ = [
    "FileMetadata",
    "FileUploadRequest",
    "FileResponse",
    "ChunkUploadRequest",
    "ChunkUploadResponse",
    "FileListResponse",
    "FileUpdateRequest",
    "FileVersionInfo",
    "SpreadsheetData",
    "SpreadsheetInfo",
    "SpreadsheetCreateRequest",
    "SpreadsheetUpdateRequest",
    "SpreadsheetReadResponse",
]

