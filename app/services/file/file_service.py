"""File service for upload, download, and management."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from app.models.file import FileMetadata, FileResponse
from app.services.base_service import BaseService

if TYPE_CHECKING:
    from app.services.data import DataService
    from app.services.file.storage.local import LocalStorage
    from app.services.logger import Logger
    from config import Config


class FileService(BaseService):
    """File upload and management service."""

    def __init__(
        self: FileService,
        logger: Logger,
        config: Config,
        data_service: DataService,
        storage_backend: LocalStorage,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize FileService.

        Args:
        ----
            logger: Logger instance.
            config: Configuration instance.
            data_service: DataService instance.
            storage_backend: Storage backend instance.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        """
        super().__init__(config, logger, *args, **kwargs)
        self.data_service = data_service
        self.storage_backend = storage_backend

        self.max_file_size = config.get("file_max_size", 1073741824)
        self.chunk_size = config.get("file_chunk_size", 5242880)
        self.allowed_types = config.get("file_allowed_types", [])
        self.versioning_enabled = config.get("file_versioning_enabled", True)
        self.image_processing_enabled = config.get(
            "file_image_processing_enabled", True
        )
        self.thumbnail_sizes = config.get("file_thumbnail_sizes", [150, 300, 600])
        self.deduplication_enabled = config.get("file_deduplication_enabled", True)

        self.chunked_upload_handler = None
        self.image_processor = None
        self.spreadsheet_processor = None

        self.spreadsheet_processing_enabled = config.get(
            "file_spreadsheet_processing_enabled", False
        )

        if self.image_processing_enabled:
            try:
                from app.services.file.image_processor import ImageProcessor

                self.image_processor = ImageProcessor(
                    logger=logger, config=config, storage_backend=storage_backend
                )
            except ImportError as e:
                self.logger.warning(f"Image processor not available: {e}")

        if self.spreadsheet_processing_enabled:
            try:
                from app.services.file.spreadsheet_processor import SpreadsheetProcessor

                self.spreadsheet_processor = SpreadsheetProcessor(
                    logger=logger, config=config, storage_backend=storage_backend
                )
                self.logger.info(
                    "Spreadsheet processor initialized successfully",
                    extra={"service": "FileService"},
                )
            except ImportError as e:
                self.logger.warning(
                    f"Spreadsheet processor not available: {e}",
                    extra={"service": "FileService"},
                )
            except Exception as e:
                self.logger.error(
                    f"Spreadsheet processor initialization failed: {e}",
                    extra={"service": "FileService"},
                    exc_info=True,
                )

        try:
            from app.services.file.chunked_upload import ChunkedUploadHandler

            self.chunked_upload_handler = ChunkedUploadHandler(
                logger=logger,
                config=config,
                cache_service=data_service.cache_service,
            )
        except ImportError as e:
            self.logger.warning(f"Chunked upload handler not available: {e}")

        self.logger.info("FileService initialized", extra={"service": "FileService"})

    def _validate_file_type(self: FileService, content_type: str) -> bool:
        """Validate file content type.

        Args:
        ----
            content_type: MIME type.

        Returns:
        -------
            True if allowed, False otherwise.

        """
        if not self.allowed_types:
            return True

        for allowed in self.allowed_types:
            if allowed.endswith("/*"):
                prefix = allowed[:-1]
                if content_type.startswith(prefix):
                    return True
            elif content_type == allowed:
                return True

        return False

    def _generate_storage_path(
        self: FileService, user_id: str, file_id: str, version: int, filename: str
    ) -> str:
        """Generate storage path for file.

        Args:
        ----
            user_id: User ID.
            file_id: File ID.
            version: File version.
            filename: Original filename.

        Returns:
        -------
            Storage path string.

        """
        # Sanitize filename but preserve more characters for better compatibility
        # Remove path separators and dangerous characters
        safe_filename = "".join(
            c for c in filename if c.isalnum() or c in ".-_()[]{} "
        ).strip()
        # Replace spaces with underscores to avoid issues
        safe_filename = safe_filename.replace(" ", "_")
        # Ensure filename is not empty
        if not safe_filename:
            safe_filename = "file"
        return f"{user_id}/{file_id}/{version}/{safe_filename}"

    async def upload_file(
        self: FileService,
        user_id: str,
        filename: str,
        content: bytes,
        content_type: str,
        *,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        version: int | None = None,
    ) -> FileResponse:
        """Upload a single file.

        Args:
        ----
            user_id: User ID.
            filename: Original filename.
            content: File content as bytes.
            content_type: MIME type.
            tags: Optional tags.
            metadata: Optional metadata.
            version: Optional version number (for new version).

        Returns:
        -------
            FileResponse with file information.

        Raises:
        ------
            ValueError: If file validation fails.

        """
        if len(content) > self.max_file_size:
            raise ValueError(f"File size exceeds maximum of {self.max_file_size} bytes")

        if not self._validate_file_type(content_type):
            raise ValueError(f"File type {content_type} not allowed")

        content_hash = self.storage_backend.compute_hash(content)

        if self.deduplication_enabled:
            existing_file = await self.data_service.files.get_file_by_hash(content_hash)
            if existing_file:
                self.logger.info(
                    f"File with hash {content_hash} already exists",
                    extra={
                        "service": "FileService",
                        "file_id": existing_file["file_id"],
                    },
                )
                return await self._file_metadata_to_response(existing_file)

        file_id = str(uuid.uuid4())
        file_version = version or 1

        if version is not None and self.versioning_enabled:
            existing = await self.data_service.files.get_file_by_id(file_id)
            if existing:
                versions = await self.data_service.files.get_file_versions(file_id)
                file_version = (
                    max((v.get("version", 0) for v in versions), default=0) + 1
                )

        storage_path = self._generate_storage_path(
            user_id, file_id, file_version, filename
        )

        saved = await self.storage_backend.save(storage_path, content, overwrite=False)
        if not saved:
            raise ValueError("Failed to save file to storage")

        thumbnail_paths = {}
        if self.image_processor and content_type.startswith("image/"):
            try:
                thumbnail_paths = await self.image_processor.process_image(
                    storage_path, content, self.thumbnail_sizes
                )
            except Exception as e:
                self.logger.warning(
                    f"Image processing failed: {e}",
                    extra={"service": "FileService"},
                )

        spreadsheet_metadata = {}
        if (
            self.spreadsheet_processor
            and self.spreadsheet_processor._is_spreadsheet_type(content_type)
        ):
            self.logger.info(
                f"Processing spreadsheet file: {filename}, type: {content_type}",
                extra={"service": "FileService", "storage_path": storage_path},
            )
            try:
                sheet_info = await self.spreadsheet_processor.get_sheet_info(
                    storage_path
                )
                spreadsheet_metadata = {
                    "sheet_names": sheet_info.get("sheet_names", []),
                    "total_sheets": sheet_info.get("total_sheets", 0),
                    "format": sheet_info.get("format", ""),
                }
                self.logger.info(
                    f"Spreadsheet metadata extracted: {spreadsheet_metadata}",
                    extra={"service": "FileService"},
                )
            except Exception as e:
                self.logger.error(
                    f"Spreadsheet metadata extraction failed: {e}",
                    extra={"service": "FileService"},
                    exc_info=True,
                )

        file_metadata = {
            "file_id": file_id,
            "user_id": user_id,
            "filename": filename,
            "content_type": content_type,
            "size": len(content),
            "hash": content_hash,
            "version": file_version,
            "storage_path": storage_path,
            "storage_backend": "local",
            "tags": tags or [],
            "metadata": {**(metadata or {}), **spreadsheet_metadata},
            "thumbnail_paths": thumbnail_paths,
        }

        await self.data_service.files.create_file_metadata(file_metadata)

        return await self._file_metadata_to_response(file_metadata)

    async def download_file(
        self: FileService, file_id: str, user_id: str | None = None
    ) -> tuple[bytes, FileMetadata] | None:
        """Download a file.

        Args:
        ----
            file_id: File ID.
            user_id: Optional user ID for access control.

        Returns:
        -------
            Tuple of (file content, file metadata) or None if not found.

        """
        file_metadata = await self.data_service.files.get_file_by_id(file_id)
        if not file_metadata:
            return None

        if user_id and file_metadata.get("user_id") != user_id:
            self.logger.warning(
                f"User {user_id} attempted to access file {file_id} owned by {file_metadata.get('user_id')}",
                extra={"service": "FileService"},
            )
            return None

        storage_path = file_metadata.get("storage_path")
        if not storage_path:
            return None

        content = await self.storage_backend.read(storage_path)
        if not content:
            return None

        return content, FileMetadata(**file_metadata)

    async def get_file_metadata(
        self: FileService, file_id: str, user_id: str | None = None
    ) -> FileResponse | None:
        """Get file metadata.

        Args:
        ----
            file_id: File ID.
            user_id: Optional user ID for access control.

        Returns:
        -------
            FileResponse or None if not found.

        """
        file_metadata = await self.data_service.files.get_file_by_id(file_id)
        if not file_metadata:
            return None

        if user_id and file_metadata.get("user_id") != user_id:
            return None

        return await self._file_metadata_to_response(file_metadata)

    async def list_files(
        self: FileService,
        user_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
        tags: list[str] | None = None,
    ) -> list[FileResponse]:
        """List files for a user.

        Args:
        ----
            user_id: User ID.
            limit: Maximum number of files.
            offset: Number of files to skip.
            tags: Optional tags filter.

        Returns:
        -------
            List of FileResponse objects.

        """
        files = await self.data_service.files.get_user_files(
            user_id, limit=limit, offset=offset, tags=tags
        )

        return [await self._file_metadata_to_response(f) for f in files]

    async def update_file_metadata(
        self: FileService,
        file_id: str,
        user_id: str,
        *,
        filename: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> FileResponse | None:
        """Update file metadata.

        Args:
        ----
            file_id: File ID.
            user_id: User ID (must own the file).
            filename: Optional new filename.
            tags: Optional new tags.
            metadata: Optional new metadata.

        Returns:
        -------
            Updated FileResponse or None if not found/unauthorized.

        """
        file_metadata = await self.data_service.files.get_file_by_id(file_id)
        if not file_metadata:
            return None

        if file_metadata.get("user_id") != user_id:
            return None

        updates: dict[str, Any] = {}
        if filename is not None:
            updates["filename"] = filename
        if tags is not None:
            updates["tags"] = tags
        if metadata is not None:
            updates["metadata"] = metadata

        await self.data_service.files.update_file_metadata(file_id, updates)

        updated = await self.data_service.files.get_file_by_id(file_id)
        return await self._file_metadata_to_response(updated) if updated else None

    async def delete_file(
        self: FileService, file_id: str, user_id: str, *, hard_delete: bool = False
    ) -> bool:
        """Delete a file.

        Args:
        ----
            file_id: File ID.
            user_id: User ID (must own the file).
            hard_delete: Whether to permanently delete.

        Returns:
        -------
            True if successful, False otherwise.

        """
        file_metadata = await self.data_service.files.get_file_by_id(file_id)
        if not file_metadata:
            return False

        if file_metadata.get("user_id") != user_id:
            return False

        if hard_delete:
            storage_path = file_metadata.get("storage_path")
            if storage_path:
                await self.storage_backend.delete(storage_path)

            for thumb_path in file_metadata.get("thumbnail_paths", {}).values():
                await self.storage_backend.delete(thumb_path)

        return await self.data_service.files.delete_file_metadata(
            file_id, hard_delete=hard_delete
        )

    async def get_file_versions(self: FileService, file_id: str) -> list[FileResponse]:
        """Get all versions of a file.

        Args:
        ----
            file_id: File ID.

        Returns:
        -------
            List of FileResponse objects for each version.

        """
        versions = await self.data_service.files.get_file_versions(file_id)
        return [await self._file_metadata_to_response(v) for v in versions]

    async def create_version(
        self: FileService,
        file_id: str,
        user_id: str,
        filename: str,
        content: bytes,
        content_type: str,
        *,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> FileResponse:
        """Create a new version of an existing file.

        Args:
        ----
            file_id: Base file ID.
            user_id: User ID.
            filename: New filename.
            content: File content.
            content_type: MIME type.
            tags: Optional tags.
            metadata: Optional metadata.

        Returns:
        -------
            FileResponse for new version.

        """
        existing = await self.data_service.files.get_file_by_id(file_id)
        if not existing or existing.get("user_id") != user_id:
            raise ValueError("File not found or unauthorized")

        versions = await self.data_service.files.get_file_versions(file_id)
        next_version = max((v.get("version", 0) for v in versions), default=0) + 1

        return await self.upload_file(
            user_id,
            filename,
            content,
            content_type,
            tags=tags,
            metadata=metadata,
            version=next_version,
        )

    async def _file_metadata_to_response(
        self: FileService, file_metadata: dict[str, Any]
    ) -> FileResponse:
        """Convert file metadata dict to FileResponse.

        Args:
        ----
            file_metadata: File metadata dictionary.

        Returns:
        -------
            FileResponse object.

        """
        storage_path = file_metadata.get("storage_path", "")
        download_url = await self.storage_backend.get_url(storage_path)

        thumbnail_urls = {}
        for size, thumb_path in file_metadata.get("thumbnail_paths", {}).items():
            thumbnail_urls[size] = await self.storage_backend.get_url(thumb_path)

        return FileResponse(
            file_id=file_metadata["file_id"],
            user_id=file_metadata["user_id"],
            filename=file_metadata["filename"],
            content_type=file_metadata["content_type"],
            size=file_metadata["size"],
            version=file_metadata.get("version", 1),
            tags=file_metadata.get("tags", []),
            metadata=file_metadata.get("metadata", {}),
            thumbnail_urls=thumbnail_urls,
            download_url=download_url,
            created_at=file_metadata.get("created_at", datetime.now(timezone.utc)),
            updated_at=file_metadata.get("updated_at", datetime.now(timezone.utc)),
        )


__all__ = ["FileService"]
