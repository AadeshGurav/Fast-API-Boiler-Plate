"""Role-based access control models with DynamicConfig support."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class TemporaryPermission(BaseModel):
    """Temporary permission model for time-bound access."""

    id: str = Field(..., description="Unique temporary permission identifier")
    entity_type: str = Field(..., description="Entity type (user or group)")
    entity_id: str = Field(..., description="Entity identifier")
    permission_id: str = Field(..., description="Permission identifier")
    start_time: datetime | None = Field(None, description="Start time (defaults to now)")
    end_time: datetime | None = Field(None, description="End time (null = permanent)")
    created_by: str = Field(..., description="User who created this temporary permission")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Creation timestamp"
    )


class TemporaryPermissionCreate(BaseModel):
    """Request body for granting a temporary permission (server fills id/created_by)."""

    entity_type: str = Field(..., pattern="^(user|group)$", description="user or group")
    entity_id: str = Field(..., description="Entity identifier")
    permission_id: str = Field(..., description="Permission identifier")
    start_time: datetime | None = Field(None, description="Start time (null = now)")
    end_time: datetime | None = Field(None, description="End time (null = until revoked)")


__all__ = [
    "TemporaryPermission",
    "TemporaryPermissionCreate",
]
