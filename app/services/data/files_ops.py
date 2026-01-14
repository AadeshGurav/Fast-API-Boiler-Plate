"""File-related data operations built on core CRUD."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from .policies import CachePolicy

if TYPE_CHECKING:
    from .data_service import DataService


class FilesOps:
    """File-related data operations."""

    def __init__(self: FilesOps, service: DataService) -> None:
        """Initialize FilesOps.

        Args:
        ----
            service: DataService instance.

        """
        self.service = service
        self.collection = "files"

    async def create_file_metadata(self: FilesOps, file_data: dict[str, Any]) -> str:
        """Create file metadata record.

        Args:
        ----
            file_data: File metadata dictionary.

        Returns:
        -------
            File ID.

        """
        file_id = file_data.get("file_id") or str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        file_data |= {
            "file_id": file_id,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }
        await self.service.set(
            self.collection,
            {"file_id": file_id},
            file_data,
            policy=CachePolicy.DB_ONLY,
        )
        return file_id

    async def get_file_by_id(
        self: FilesOps, file_id: str, *, include_deleted: bool = False
    ) -> dict | None:
        """Get file metadata by ID.

        Args:
        ----
            file_id: File ID.
            include_deleted: Whether to include soft-deleted files.

        Returns:
        -------
            File metadata dictionary or None if not found.

        """
        filters = {"file_id": file_id}
        if not include_deleted:
            filters["deleted_at"] = None

        return await self.service.get(self.collection, filters, policy=CachePolicy.AUTO)

    async def get_file_by_hash(
        self: FilesOps, content_hash: str, *, include_deleted: bool = False
    ) -> dict | None:
        """Get file metadata by content hash.

        Args:
        ----
            content_hash: SHA256 hash of file content.
            include_deleted: Whether to include soft-deleted files.

        Returns:
        -------
            File metadata dictionary or None if not found.

        """
        filters = {"hash": content_hash}
        if not include_deleted:
            filters["deleted_at"] = None

        return await self.service.get(self.collection, filters, policy=CachePolicy.AUTO)

    async def get_user_files(
        self: FilesOps,
        user_id: str,
        *,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0,
        tags: list[str] | None = None,
    ) -> list[dict]:
        """Get files for a user.

        Args:
        ----
            user_id: User ID.
            include_deleted: Whether to include soft-deleted files.
            limit: Maximum number of files to return.
            offset: Number of files to skip.
            tags: Optional list of tags to filter by.

        Returns:
        -------
            List of file metadata dictionaries.

        """
        filters: dict[str, Any] = {"user_id": user_id}
        if not include_deleted:
            filters["deleted_at"] = None

        if tags:
            filters["tags"] = {"$in": tags}

        files = await self.service.find_many(
            self.collection, filters, policy=CachePolicy.AUTO
        )

        return files[offset: offset + limit]

    async def update_file_metadata(
        self: FilesOps, file_id: str, updates: dict[str, Any]
    ) -> bool:
        """Update file metadata.

        Args:
        ----
            file_id: File ID.
            updates: Update dictionary.

        Returns:
        -------
            True if successful, False otherwise.

        """
        updates = {**updates, "updated_at": datetime.now(timezone.utc)}
        return await self.service.set(
            self.collection,
            {"file_id": file_id},
            updates,
            policy=CachePolicy.DB_ONLY,
        )

    async def delete_file_metadata(
        self: FilesOps, file_id: str, *, hard_delete: bool = False
    ) -> bool:
        """Delete file metadata (soft delete by default).

        Args:
        ----
            file_id: File ID.
            hard_delete: Whether to permanently delete.

        Returns:
        -------
            True if successful, False otherwise.

        """
        if hard_delete:
            return await self.service.delete(
                self.collection, {"file_id": file_id}, policy=CachePolicy.DB_ONLY
            )

        return await self.update_file_metadata(
            file_id, {"deleted_at": datetime.now(timezone.utc)}
        )

    async def get_file_versions(self: FilesOps, file_id: str) -> list[dict]:
        """Get all versions of a file.

        Args:
        ----
            file_id: File ID (base file ID, not version-specific).

        Returns:
        -------
            List of file version dictionaries.

        """
        file_metadata = await self.get_file_by_id(file_id, include_deleted=True)
        if not file_metadata:
            return []

        base_file_id = file_metadata.get("file_id")
        filters = {"file_id": base_file_id, "deleted_at": None}

        versions = await self.service.find_many(
            self.collection, filters, policy=CachePolicy.AUTO
        )

        return sorted(versions, key=lambda x: x.get("version", 0), reverse=True)

    async def get_latest_version(self: FilesOps, file_id: str) -> dict | None:
        """Get latest version of a file.

        Args:
        ----
            file_id: File ID.

        Returns:
        -------
            Latest file version dictionary or None.

        """
        versions = await self.get_file_versions(file_id)
        return versions[0] if versions else None

    async def search_files(
        self: FilesOps,
        *,
        user_id: str | None = None,
        tags: list[str] | None = None,
        content_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Search files with filters.

        Args:
        ----
            user_id: Optional user ID filter.
            tags: Optional tags filter.
            content_type: Optional content type filter.
            limit: Maximum number of files to return.
            offset: Number of files to skip.

        Returns:
        -------
            List of file metadata dictionaries.

        """
        filters: dict[str, Any] = {"deleted_at": None}

        if user_id:
            filters["user_id"] = user_id

        if tags:
            filters["tags"] = {"$in": tags}

        if content_type:
            filters["content_type"] = content_type

        files = await self.service.find_many(
            self.collection, filters, policy=CachePolicy.AUTO
        )

        return files[offset: offset + limit]


__all__ = ["FilesOps"]
