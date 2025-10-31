"""Authentication models for login, tokens, and password reset."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import Field

from app.core.dynamic_config import DynamicConfig

if TYPE_CHECKING:
    # Type-only imports to avoid runtime import cost and cycles
    from app.models.session import DeviceInfo
    from app.models.user import UserPublic


class TokenPair(DynamicConfig):
    """Token pair model."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")


class TokenPayload(DynamicConfig):
    """JWT token payload model."""

    user_id: str = Field(..., description="User identifier")
    username: str = Field(..., description="Username")
    roles: list[str] = Field(default_factory=list, description="User roles")
    permissions: list[str] = Field(
        default_factory=list, description="Resolved permissions"
    )
    exp: datetime = Field(..., description="Token expiration")
    iat: datetime = Field(
        default_factory=datetime.utcnow, description="Token issued at"
    )
    type: str = Field(..., description="Token type (access or refresh)")


class LoginRequest(DynamicConfig):
    """Login request model."""

    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
    device_info: DeviceInfo = Field(..., description="Device information")


class RegisterRequest(DynamicConfig):
    """User registration request model."""

    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    newsletter: bool = Field(default=False, description="Subscribe to newsletter")


class LoginResponse(DynamicConfig):
    """Login response model."""

    user: UserPublic = Field(..., description="User information")
    tokens: TokenPair = Field(..., description="Token pair")
    permissions: list[str] = Field(..., description="Resolved user permissions")


class RefreshRequest(DynamicConfig):
    """Token refresh request model."""

    refresh_token: str = Field(..., description="Refresh token")
    device_info: DeviceInfo = Field(..., description="Device information")


class PasswordResetRequest(DynamicConfig):
    """Password reset request model."""

    email: str = Field(..., description="User email address")


class PasswordResetConfirm(DynamicConfig):
    """Password reset confirmation model."""

    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., min_length=8, description="New password")


__all__ = [
    "TokenPair",
    "TokenPayload",
    "LoginRequest",
    "RegisterRequest",
    "LoginResponse",
    "RefreshRequest",
    "PasswordResetRequest",
    "PasswordResetConfirm",
]
