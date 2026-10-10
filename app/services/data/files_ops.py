"""File metadata operations.

A *file* is identified by ``file_id`` and has one or more *versions*; each version is its
own record (``file_id`` + ``version``) pointing at its own stored bytes. Reads of file
metadata go straight to the database: ownership and soft-delete state decide who may
download, so they must never be served from a cache.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
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
        """Record one version of a file and make it the file's current (latest) one.

        ``is_latest`` is denormalised onto the records so listings can filter, sort and
        page in the database instead of grouping versions in application memory. The new
        version is inserted first, then older ones are demoted, so a reader never sees a
        file with no current version.

        Args:
        ----
            file_data: Metadata including ``file_id`` and ``version``.

        Returns:
        -------
            The file id.

        """
        file_id = file_data.get("file_id") or str(uuid.uuid4())
        version = file_data.get("version", 1)
        now = datetime.now(UTC)
        await self.service.insert(
            self.collection,
            {
                **file_data,
                "file_id": file_id,
                "version": version,
                "is_latest": True,
                "created_at": now,
                "updated_at": now,
                "deleted_at": None,
            },
        )
        await self.service.update_many(
            self.collection,
            {"file_id": file_id, "is_latest": True, "version": {"$lt": version}},
            {"is_latest": False},
        )
        return file_id

    async def get_file_versions(
        self: FilesOps, file_id: str, *, include_deleted: bool = False
    ) -> list[dict]:
        """All versions of a file, newest first."""
        filters: dict[str, Any] = {"file_id": file_id}
        if not include_deleted:
            filters["deleted_at"] = None
        return await self.service.find_many(self.collection, filters, sort=[("version", -1)])

    async def user_storage_bytes(self: FilesOps, user_id: str) -> int:
        """Bytes a user occupies: every stored version, soft-deleted ones included.

        ponytail: sums up to the database's result cap (10 000 versions); a counter on the
        user record is the upgrade if a single user can legitimately hold more.
        """
        records = await self.service.find_many(self.collection, {"user_id": user_id})
        return sum(int(r.get("size") or 0) for r in records)

    async def get_file_by_id(
        self: FilesOps,
        file_id: str,
        *,
        version: int | None = None,
        include_deleted: bool = False,
    ) -> dict | None:
        """One version of a file: the newest unless ``version`` is given."""
        filters: dict[str, Any] = {"file_id": file_id}
        if version is not None:
            filters["version"] = version
        if not include_deleted:
            filters["deleted_at"] = None
        found = await self.service.find_many(
            self.collection, filters, sort=[("version", -1)], limit=1
        )
        return found[0] if found else None

    async def get_file_by_hash(self: FilesOps, content_hash: str, user_id: str) -> dict | None:
        """A live file of ``user_id`` with this content (never another user's)."""
        return await self.service.get(
            self.collection,
            {"hash": content_hash, "user_id": user_id, "deleted_at": None},
            policy=CachePolicy.DB_ONLY,
        )

    async def get_user_files(
        self: FilesOps,
        user_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
        tags: list[str] | None = None,
    ) -> tuple[list[dict], int]:
        """A page of a user's files (newest version of each), newest first, plus the total."""
        filters: dict[str, Any] = {"user_id": user_id, "is_latest": True, "deleted_at": None}
        if tags:
            filters["tags"] = {"$in": tags}
        page = await self.service.find_many(
            self.collection, filters, limit=limit, skip=offset, sort=[("created_at", -1)]
        )
        return page, await self.service.count(self.collection, filters)

    async def update_file_metadata(self: FilesOps, file_id: str, updates: dict[str, Any]) -> bool:
        """Change metadata of the newest version; False if the file does not exist."""
        latest = await self.get_file_by_id(file_id)
        if latest is None:
            return False
        return await self.service.update(
            self.collection,
            {"file_id": file_id, "version": latest["version"]},
            {**updates, "updated_at": datetime.now(UTC)},
            policy=CachePolicy.DB_ONLY,
        )

    async def delete_file_metadata(
        self: FilesOps, file_id: str, *, hard_delete: bool = False
    ) -> bool:
        """Delete every version (soft by default); False if there was nothing to delete."""
        versions = await self.get_file_versions(file_id, include_deleted=hard_delete)
        if not versions:
            return False

        if hard_delete:
            for record in versions:
                await self.service.delete(
                    self.collection,
                    {"file_id": file_id, "version": record["version"]},
                    policy=CachePolicy.DB_ONLY,
                )
        else:
            now = datetime.now(UTC)
            await self.service.update_many(
                self.collection,
                {"file_id": file_id, "deleted_at": None},
                {"deleted_at": now, "updated_at": now},
            )
        return True


__all__ = ["FilesOps"]
