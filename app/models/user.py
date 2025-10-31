"""User models for authentication and user management."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import EmailStr, Field

from app.core.dynamic_config import DynamicConfig


class UserRole(str, Enum):
    """User role enumeration."""

    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    GUEST = "guest"


class UserStatus(str, Enum):
    """User status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class User(DynamicConfig):
    """User model for API validation."""

    id: str = Field(..., description="Unique user identifier")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="User email address")
    password_hash: str | None = Field(None, description="Hashed password")
    roles: list[str] = Field(default_factory=list, description="User roles")
    groups: list[str] = Field(default_factory=list, description="User groups")
    status: UserStatus = Field(default=UserStatus.ACTIVE, description="User status")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional user metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )


class UserCreate(DynamicConfig):
    """User creation model."""

    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Plain text password")
    roles: list[str] = Field(default_factory=list, description="Initial roles")
    groups: list[str] = Field(default_factory=list, description="Initial groups")


class UserUpdate(DynamicConfig):
    """User update model."""

    email: EmailStr | None = Field(None, description="Updated email address")
    roles: list[str] | None = Field(None, description="Updated roles")
    groups: list[str] | None = Field(None, description="Updated groups")
    status: UserStatus | None = Field(None, description="Updated status")
    metadata: dict[str, Any] | None = Field(None, description="Updated metadata")


class UserInDB(User):
    """User model with password hash for database storage."""

    password_hash: str = Field(..., description="Hashed password")


class UserPublic(DynamicConfig):
    """Safe user data for API responses (no password_hash)."""

    id: str = Field(..., description="Unique user identifier")
    username: str = Field(..., description="Username")
    email: EmailStr = Field(..., description="User email address")
    roles: list[str] = Field(default_factory=list, description="User roles")
    groups: list[str] = Field(default_factory=list, description="User groups")
    status: UserStatus = Field(..., description="User status")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional user metadata"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


__all__ = [
    "UserRole",
    "UserStatus",
    "User",
    "UserCreate",
    "UserUpdate",
    "UserInDB",
    "UserPublic",
]
