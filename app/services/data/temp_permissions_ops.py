"""Time-limited permission grants (the only RBAC data that lives in the database)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from .policies import CachePolicy

if TYPE_CHECKING:
    from .data_service import DataService


class TemporaryPermissionsOps:
    """Grants of a permission to a user or group between ``start_time`` and ``end_time``."""

    collection = "temporary_permissions"

    def __init__(self, service: DataService) -> None:
        self.service = service

    async def create(self, grant: dict[str, Any]) -> str:
        """Store a grant; returns its id."""
        grant_id = uuid.uuid4().hex
        await self.service.insert(
            self.collection, {**grant, "id": grant_id, "created_at": datetime.now(UTC)}
        )
        return grant_id

    async def get_active(self, entity_type: str, entity_id: str) -> list[dict[str, Any]]:
        """Grants for the entity that are started, unexpired and unrevoked."""
        now = datetime.now(UTC)
        # ``{field: None}`` matches both null and missing fields.
        return await self.service.find_many(
            self.collection,
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "revoked_at": None,
                "$and": [
                    {"$or": [{"start_time": None}, {"start_time": {"$lte": now}}]},
                    {"$or": [{"end_time": None}, {"end_time": {"$gt": now}}]},
                ],
            },
            policy=CachePolicy.DB_ONLY,
        )

    async def get(self, grant_id: str) -> dict[str, Any] | None:
        """One grant by id."""
        return await self.service.get(self.collection, {"id": grant_id}, policy=CachePolicy.DB_ONLY)

    async def revoke(self, grant_id: str) -> bool:
        """Mark a grant revoked; False if it does not exist."""
        return await self.service.update(
            self.collection,
            {"id": grant_id},
            {"revoked_at": datetime.now(UTC)},
            policy=CachePolicy.DB_ONLY,
        )
