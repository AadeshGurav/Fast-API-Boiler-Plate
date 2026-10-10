"""User models for authentication and user management."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class UserRole(StrEnum):
    """User role enumeration."""

    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    GUEST = "guest"


class UserStatus(StrEnum):
    """User status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class User(BaseModel):
    """User model for API validation."""

    id: str = Field(..., description="Unique user identifier")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    # Plain str: addresses are validated on the way in (UserCreate, UserUpdate); re-checking
    # a stored address on every read or response costs a syntax/IDNA pass per request.
    email: str = Field(..., description="User email address")
    password_hash: str | None = Field(None, description="Hashed password")
    roles: list[str] = Field(default_factory=list, description="User roles")
    groups: list[str] = Field(default_factory=list, description="User groups")
    status: UserStatus = Field(default=UserStatus.ACTIVE, description="User status")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional user metadata")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last update timestamp"
    )


class UserCreate(BaseModel):
    """User creation model."""

    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="Plain text password")
    roles: list[str] = Field(default_factory=list, description="Initial roles")
    groups: list[str] = Field(default_factory=list, description="Initial groups")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional user metadata")


class UserUpdate(BaseModel):
    """User update model."""

    email: EmailStr | None = Field(None, description="Updated email address")
    roles: list[str] | None = Field(None, description="Updated roles")
    groups: list[str] | None = Field(None, description="Updated groups")
    status: UserStatus | None = Field(None, description="Updated status")
    metadata: dict[str, Any] | None = Field(None, description="Updated metadata")


class UserInDB(User):
    """User model with password hash for database storage."""

    password_hash: str = Field(..., description="Hashed password")


class UserPublic(BaseModel):
    """Safe user data for API responses (no password_hash)."""

    id: str = Field(..., description="Unique user identifier")
    username: str = Field(..., description="Username")
    # Plain str: addresses are validated on the way in (UserCreate, UserUpdate); re-checking
    # a stored address on every read or response costs a syntax/IDNA pass per request.
    email: str = Field(..., description="User email address")
    roles: list[str] = Field(default_factory=list, description="User roles")
    groups: list[str] = Field(default_factory=list, description="User groups")
    status: UserStatus = Field(..., description="User status")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional user metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class UserListResponse(BaseModel):
    """One page of users."""

    users: list[UserPublic]
    total: int
    page: int
    page_size: int
    has_next: bool


class UserStatusUpdate(BaseModel):
    """Administrative change of an account's status."""

    status: UserStatus


__all__ = [
    "User",
    "UserCreate",
    "UserInDB",
    "UserListResponse",
    "UserPublic",
    "UserRole",
    "UserStatus",
    "UserStatusUpdate",
    "UserUpdate",
]
