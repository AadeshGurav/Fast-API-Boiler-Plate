"""Versioned, run-once data migrations.

Applied versions are recorded in the ``schema_migrations`` collection. Each migration must
be idempotent: several workers may start at once and each runs whatever is missing.
Add new migrations to the end of ``MIGRATIONS`` with the next version number; never edit
or reorder released ones.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from app.services.database_service import DatabaseService
    from app.services.logger import Logger

COLLECTION = "schema_migrations"


@dataclass(frozen=True)
class Migration:
    version: int
    description: str
    apply: Callable[[DatabaseService], Awaitable[None]]


async def _drop_superseded_indexes(db: DatabaseService) -> None:
    await db.drop_indexes(
        {
            # a unique file_id made file versions impossible
            "files": ["file_id_1", "hash_1", "user_id_1", "created_at_-1", "deleted_at_1"],
            "sessions": ["revoked_at_1", "user_id_1"],
            # RBAC definitions moved from the database into configuration
            "roles": ["id_1", "name_1"],
            "permissions": ["id_1", "name_1"],
            "groups": ["id_1", "name_1"],
            "settings": ["site_name_1"],
        }
    )


BACKFILL_BATCH = 500


async def _flag_latest_file_versions(db: DatabaseService) -> None:
    """Give every file record the ``is_latest`` flag the paged listing relies on."""
    while batch := await db.find_many(
        "files", {"is_latest": {"$exists": False}}, limit=BACKFILL_BATCH
    ):
        for file_id in {record["file_id"] for record in batch}:
            versions = await db.find_many("files", {"file_id": file_id})
            newest = max(record.get("version", 1) for record in versions)
            await db.update_many(
                "files", {"file_id": file_id, "version": newest}, {"is_latest": True}
            )
            await db.update_many(
                "files", {"file_id": file_id, "is_latest": {"$exists": False}}, {"is_latest": False}
            )
    await db.drop_indexes({"files": ["user_id_1_created_at_-1", "tags_1"]})


MIGRATIONS: list[Migration] = [
    Migration(1, "drop indexes superseded by the current schema", _drop_superseded_indexes),
    Migration(2, "flag the newest version of every file (is_latest)", _flag_latest_file_versions),
]


async def run_migrations(db: DatabaseService, logger: Logger) -> list[int]:
    """Apply every migration not yet recorded; returns the versions applied."""
    applied = {row["version"] for row in await db.find_many(COLLECTION, {})}
    ran: list[int] = []
    for migration in sorted(MIGRATIONS, key=lambda m: m.version):
        if migration.version in applied:
            continue
        logger.info(f"Applying migration {migration.version}: {migration.description}")
        await migration.apply(db)
        await db.insert_record(
            COLLECTION,
            {
                "version": migration.version,
                "description": migration.description,
                "applied_at": datetime.now(UTC),
            },
        )
        ran.append(migration.version)
    return ran
