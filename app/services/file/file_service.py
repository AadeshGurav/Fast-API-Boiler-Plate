"""File service for upload, download, and management."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.models.file import FileResponse
from app.services.base_service import BaseService
from app.services.file.chunked_upload import ChunkedUploadHandler
from app.services.file.spreadsheet_processor import SpreadsheetProcessor
from app.services.file.streams import MeteredStream, iter_bytes

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    from app.core.interfaces.storage_interface import StorageInterface
    from app.services.data import DataService
    from app.services.logger import Logger
    from config import Config


MAX_FILENAME_LENGTH = 255
# Where AppFactory mounts the file routes; download and thumbnail URLs are built from it.
FILES_URL_PREFIX = "/api/v1/files"


MIME_TYPE = re.compile(r"[\w.+-]+/[\w.+-]+[ \t]*(;[ \t\x21-\x7e]*)?")


class FileService(BaseService):
    """File upload and management service."""

    def __init__(
        self: FileService,
        logger: Logger,
        config: Config,
        data_service: DataService,
        storage_backend: StorageInterface,
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

        self.max_file_size = config["file_max_size"]
        self.chunk_size = config["file_chunk_size"]
        self.user_quota: int = config["file_user_quota_bytes"]
        self.max_versions: int = config["file_max_versions"]
        self.allowed_types = config["file_allowed_types"]
        # Types a browser would render as active content if ever served inline.
        self.blocked_types = set(config["file_blocked_types"])
        self.versioning_enabled = config["file_versioning_enabled"]
        self.image_processing_enabled = config["file_image_processing_enabled"]
        self.thumbnail_sizes = config["file_thumbnail_sizes"]
        self.deduplication_enabled = config["file_deduplication_enabled"]
        self.storage_name: str = config["file_storage_backend"]
        self.download_redirect: bool = config["file_download_redirect"]
        self.download_url_ttl: int = config["file_download_url_ttl"]

        self.image_processor = None
        self.spreadsheet_processor = None

        self.spreadsheet_processing_enabled = config["file_spreadsheet_processing_enabled"]

        if self.image_processing_enabled:
            try:
                from app.services.file.image_processor import ImageProcessor

                self.image_processor = ImageProcessor(
                    logger=logger, config=config, storage_backend=storage_backend
                )
            except ImportError as e:
                self.logger.warning(f"Image processor not available: {e}")

        if self.spreadsheet_processing_enabled:
            self.spreadsheet_processor = SpreadsheetProcessor(
                logger=logger, config=config, storage_backend=storage_backend
            )

        self.chunked_upload_handler = ChunkedUploadHandler(
            logger=logger,
            config=config,
            cache_service=data_service.cache_service,
            storage_backend=storage_backend,
        )

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
        if not MIME_TYPE.fullmatch(content_type):  # also rejects CR/LF and other control chars
            return False
        content_type = content_type.split(";")[0].strip().lower()
        if content_type in self.blocked_types:
            return False
        if not self.allowed_types:
            return True

        for allowed in self.allowed_types:
            if allowed.endswith("/*"):
                if content_type.startswith(allowed[:-1]):
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
        safe_filename = "".join(c for c in filename if c.isalnum() or c in ".-_()[]{} ").strip()
        # Replace spaces with underscores to avoid issues
        safe_filename = safe_filename.replace(" ", "_")
        # Ensure filename is not empty
        if not safe_filename or not safe_filename.strip("."):  # empty, ".", ".." ...
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
        file_id: str | None = None,
    ) -> FileResponse:
        """:meth:`upload_stream` for content that is already in memory."""
        return await self.upload_stream(
            user_id,
            filename,
            iter_bytes(content),
            content_type,
            tags=tags,
            metadata=metadata,
            file_id=file_id,
        )

    async def _check_quota(self: FileService, user_id: str, incoming: int = 0) -> None:
        """Refuse work that would take a user past ``file_user_quota_bytes`` (0 = no limit)."""
        if not self.user_quota:
            return
        used = await self.data_service.files.user_storage_bytes(user_id)
        if used + incoming > self.user_quota:
            raise ValueError(
                f"Storage quota of {self.user_quota} bytes exceeded; delete files to free space"
            )

    def _check_version_limit(self: FileService, latest: dict[str, Any]) -> None:
        if latest["version"] >= self.max_versions:
            raise ValueError(f"A file can have at most {self.max_versions} versions")

    async def upload_stream(
        self: FileService,
        user_id: str,
        filename: str,
        chunks: AsyncIterator[bytes],
        content_type: str,
        *,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        file_id: str | None = None,
    ) -> FileResponse:
        """Store a new file, or a new version of one of the caller's files.

        The bytes flow from ``chunks`` to the storage backend while being counted and
        hashed, so memory use does not depend on the file size.

        Args:
        ----
            user_id: Owner.
            filename: Original filename.
            chunks: File content.
            content_type: MIME type (as declared by the client).
            tags: Optional tags.
            metadata: Optional metadata.
            file_id: Existing file to add a version to; omit to create a new file.

        Returns:
        -------
            FileResponse with file information.

        Raises:
        ------
            ValueError: If validation fails or ``file_id`` is not the caller's file.

        """
        if not 0 < len(filename) <= MAX_FILENAME_LENGTH:
            raise ValueError(f"Filename must be 1-{MAX_FILENAME_LENGTH} characters")
        if not self._validate_file_type(content_type):
            raise ValueError(f"File type {content_type} not allowed")

        if file_id is None:
            file_id, file_version = str(uuid.uuid4()), 1
        else:
            latest = await self.get_owned(file_id, user_id)
            if latest is None:
                raise ValueError("File not found")
            if not self.versioning_enabled:
                raise ValueError("File versioning is disabled")
            self._check_version_limit(latest)
            file_version = latest["version"] + 1

        await self._check_quota(user_id)  # cheap early refusal before any bytes are stored
        storage_path = self._generate_storage_path(user_id, file_id, file_version, filename)
        stream = MeteredStream(chunks, self.max_file_size)
        if not await self.storage_backend.save_stream(storage_path, stream, overwrite=False):
            raise ValueError("Failed to save file to storage")
        if stream.size == 0:
            await self.storage_backend.delete(storage_path)
            raise ValueError("File is empty")
        try:
            await self._check_quota(user_id, stream.size)
        except ValueError:
            await self.storage_backend.delete(storage_path)
            raise

        # Same bytes, same owner: hand back the existing file. Never across users: that
        # would leak another user's file id and drop this user's upload.
        if self.deduplication_enabled and file_version == 1:
            existing = await self.data_service.files.get_file_by_hash(stream.hexdigest, user_id)
            if existing:
                await self.storage_backend.delete(storage_path)
                return self._file_metadata_to_response(existing)

        thumbnail_paths = await self._make_thumbnails(storage_path, content_type)
        spreadsheet_metadata = await self._describe_spreadsheet(storage_path, content_type)

        file_metadata = {
            "file_id": file_id,
            "user_id": user_id,
            "filename": filename,
            "content_type": content_type,
            "size": stream.size,
            "hash": stream.hexdigest,
            "version": file_version,
            "storage_path": storage_path,
            "storage_backend": self.storage_name,
            "tags": tags or [],
            "metadata": {**(metadata or {}), **spreadsheet_metadata},
            "thumbnail_paths": thumbnail_paths,
        }
        try:
            await self.data_service.files.create_file_metadata(file_metadata)
        except Exception:
            # Without its record the stored bytes could never be reached or deleted.
            for path in [storage_path, *thumbnail_paths.values()]:
                await self.storage_backend.delete(path)
            raise
        return self._file_metadata_to_response(file_metadata)

    async def _make_thumbnails(self: FileService, storage_path: str, content_type: str) -> dict:
        """Thumbnails for an image upload ({} for other files or when processing fails)."""
        if not (self.image_processor and content_type.startswith("image/")):
            return {}
        try:
            content = await self.storage_backend.read(storage_path)
            if content is None:
                return {}
            return await self.image_processor.process_image(
                storage_path, content, self.thumbnail_sizes
            )
        except Exception as e:
            self.logger.warning(f"Image processing failed: {e}", extra={"service": "FileService"})
            return {}

    async def _describe_spreadsheet(
        self: FileService, storage_path: str, content_type: str
    ) -> dict[str, Any]:
        """Sheet names and format of a spreadsheet upload ({} for other files)."""
        processor = self.spreadsheet_processor
        if not (processor and processor._is_spreadsheet_type(content_type)):
            return {}
        try:
            info = await processor.get_sheet_info(storage_path)
        except Exception as e:
            self.logger.error(
                f"Spreadsheet metadata extraction failed: {e}",
                extra={"service": "FileService", "storage_path": storage_path},
                exc_info=True,
            )
            return {}
        return {
            "sheet_names": info.get("sheet_names", []),
            "total_sheets": info.get("total_sheets", 0),
            "format": info.get("format", ""),
        }

    async def get_file_metadata(
        self: FileService, file_id: str, user_id: str
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
        if not file_metadata or file_metadata.get("user_id") != user_id:
            return None

        return self._file_metadata_to_response(file_metadata)

    async def list_files(
        self: FileService,
        user_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
        tags: list[str] | None = None,
    ) -> tuple[list[FileResponse], int]:
        """List a user's files (newest version of each).

        Returns:
        -------
            The requested page and the total number of matching files.

        """
        files, total = await self.data_service.files.get_user_files(
            user_id, limit=limit, offset=offset, tags=tags
        )
        return [self._file_metadata_to_response(f) for f in files], total

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
        return self._file_metadata_to_response(updated) if updated else None

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
        # A soft-deleted file still occupies storage and quota: it must be purgeable.
        file_metadata = await self.data_service.files.get_file_by_id(
            file_id, include_deleted=hard_delete
        )
        if not file_metadata:
            return False

        if file_metadata.get("user_id") != user_id:
            return False

        if hard_delete:
            for record in await self.data_service.files.get_file_versions(
                file_id, include_deleted=True
            ):
                paths = [record.get("storage_path"), *record.get("thumbnail_paths", {}).values()]
                for path in filter(None, paths):
                    await self.storage_backend.delete(path)

        return await self.data_service.files.delete_file_metadata(file_id, hard_delete=hard_delete)

    async def get_file_versions(
        self: FileService, file_id: str, user_id: str
    ) -> list[FileResponse]:
        """All versions of one of the caller's files, newest first (empty if not theirs)."""
        versions = await self.data_service.files.get_file_versions(file_id)
        if not versions or versions[0].get("user_id") != user_id:
            return []
        return [self._file_metadata_to_response(v) for v in versions]

    async def get_owned(
        self: FileService, file_id: str, user_id: str, *, version: int | None = None
    ) -> dict[str, Any] | None:
        """Raw metadata of a version (default: newest) if it belongs to ``user_id``."""
        record = await self.data_service.files.get_file_by_id(file_id, version=version)
        if not record or record.get("user_id") != user_id:
            return None
        return record

    async def modify_as_new_version(
        self: FileService,
        file_id: str,
        user_id: str,
        mutate: Callable[[str], Awaitable[bool]],
    ) -> FileResponse | None:
        """Edit a file in place *as a new version*, leaving earlier versions intact.

        The newest version is copied to the next version's path, ``mutate`` edits that
        copy through its storage path, and the result is recorded with its own size and
        hash. Returns None if the file is not the caller's or ``mutate`` reports failure.
        """
        latest = await self.get_owned(file_id, user_id)
        if latest is None:
            return None
        self._check_version_limit(latest)
        await self._check_quota(user_id, latest["size"])  # the copy is at least this big
        source = await self.storage_backend.open_stream(latest["storage_path"])
        if source is None:
            return None

        version = latest["version"] + 1
        new_path = self._generate_storage_path(user_id, file_id, version, latest["filename"])
        if not await self.storage_backend.save_stream(new_path, source, overwrite=False):
            return None

        try:
            if not await mutate(new_path):
                await self.storage_backend.delete(new_path)
                return None
            edited = await self.storage_backend.open_stream(new_path)
            measured = MeteredStream(edited or iter_bytes(b""), self.max_file_size)
            await measured.drain()
        except Exception:
            await self.storage_backend.delete(new_path)
            raise
        if measured.size == 0:
            await self.storage_backend.delete(new_path)
            return None

        record = {
            k: v
            for k, v in latest.items()
            if k not in {"id", "created_at", "updated_at", "deleted_at"}
        }
        record.update(
            version=version,
            storage_path=new_path,
            size=measured.size,
            hash=measured.hexdigest,
            thumbnail_paths={},
        )
        await self.data_service.files.create_file_metadata(record)
        return self._file_metadata_to_response(record)

    def _file_metadata_to_response(
        self: FileService, file_metadata: dict[str, Any]
    ) -> FileResponse:
        """API view of a metadata record. URLs point at this API (which checks ownership
        on every download), never at the storage location."""
        base = f"{FILES_URL_PREFIX}/{file_metadata['file_id']}"
        version = file_metadata.get("version", 1)
        return FileResponse(
            file_id=file_metadata["file_id"],
            user_id=file_metadata["user_id"],
            filename=file_metadata["filename"],
            content_type=file_metadata["content_type"],
            size=file_metadata["size"],
            version=version,
            tags=file_metadata.get("tags", []),
            metadata=file_metadata.get("metadata", {}),
            thumbnail_urls={
                size: f"{base}/thumbnails/{size}?version={version}"
                for size in file_metadata.get("thumbnail_paths", {})
            },
            download_url=f"{base}?version={version}",
            created_at=file_metadata.get("created_at", datetime.now(UTC)),
            updated_at=file_metadata.get("updated_at", datetime.now(UTC)),
        )


__all__ = ["FileService"]
