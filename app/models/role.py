"""Role-based access control models with DynamicConfig support."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.core.dynamic_config import DynamicConfig


class Permission(DynamicConfig):
    """Permission model with JSON-driven configuration."""

    id: str = Field(..., description="Unique permission identifier")
    name: str = Field(..., description="Permission name")
    description: str = Field(..., description="Permission description")
    resource: str | None = Field(
        None, description="Resource this permission applies to"
    )
    action: str | None = Field(None, description="Action this permission allows")


class Role(DynamicConfig):
    """Role model with inheritance support and JSON-driven configuration."""

    id: str = Field(..., description="Unique role identifier")
    name: str = Field(..., description="Role name")
    permissions: list[str] = Field(
        default_factory=list, description="List of permission IDs"
    )
    inherits: list[str] = Field(
        default_factory=list, description="List of role IDs to inherit from"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional role metadata"
    )


class Group(DynamicConfig):
    """Group model for role aggregation with JSON-driven configuration."""

    id: str = Field(..., description="Unique group identifier")
    name: str = Field(..., description="Group name")
    roles: list[str] = Field(default_factory=list, description="List of role IDs")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional group metadata"
    )


class TemporaryPermission(DynamicConfig):
    """Temporary permission model for time-bound access."""

    id: str = Field(..., description="Unique temporary permission identifier")
    entity_type: str = Field(..., description="Entity type (user or group)")
    entity_id: str = Field(..., description="Entity identifier")
    permission_id: str = Field(..., description="Permission identifier")
    start_time: datetime | None = Field(
        None, description="Start time (defaults to now)"
    )
    end_time: datetime | None = Field(None, description="End time (null = permanent)")
    created_by: str = Field(
        ..., description="User who created this temporary permission"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )


__all__ = ["Permission", "Role", "Group", "TemporaryPermission"]
