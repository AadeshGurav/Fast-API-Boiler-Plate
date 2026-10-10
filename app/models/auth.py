"""Authentication models for login, tokens, and password reset."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, EmailStr, Field

# Import at runtime so Pydantic can resolve annotations during schema generation
from app.models.session import DeviceInfo
from app.models.user import UserPublic


class TokenPair(BaseModel):
    """Token pair model."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")


class TokenPayload(BaseModel):
    """JWT token payload model."""

    user_id: str = Field(..., description="User identifier")
    username: str = Field(..., description="Username")
    roles: list[str] = Field(default_factory=list, description="User roles")
    permissions: list[str] = Field(default_factory=list, description="Resolved permissions")
    exp: datetime = Field(..., description="Token expiration")
    iat: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Token issued at",
    )
    type: str = Field(..., description="Token type (access or refresh)")
    sid: str | None = Field(
        None, description="Session the token belongs to; revoking it kills the token"
    )
    jti: str = Field(
        default_factory=lambda: uuid.uuid4().hex,
        description="Unique token id (makes every issued token distinct)",
    )
    remember_me: bool = Field(default=False, description="Long-lived session chosen at login")
    scopes: list[str] | None = Field(
        None, description="For API tokens: the permissions the token is limited to"
    )


class LoginRequest(BaseModel):
    """Login request model."""

    username: str = Field(..., min_length=1, max_length=64, description="Username")
    password: str = Field(..., max_length=128, description="Password")
    remember_me: bool = Field(default=False, description="Remember user for 30 days")
    device_info: DeviceInfo | None = Field(
        None, description="Device information (added server-side)"
    )


class RegisterRequest(BaseModel):
    """User registration request model."""

    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password")
    first_name: str = Field(..., max_length=100, description="First name")
    last_name: str = Field(..., max_length=100, description="Last name")
    newsletter: bool = Field(default=False, description="Subscribe to newsletter")


class ChangePasswordRequest(BaseModel):
    """Change the signed-in user's password."""

    current_password: str = Field(..., max_length=128, description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")


class ProfileUpdate(BaseModel):
    """Editable parts of one's own profile."""

    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)


class LoginResponse(BaseModel):
    """Login response model."""

    user: UserPublic = Field(..., description="User information")
    tokens: TokenPair = Field(..., description="Token pair")
    permissions: list[str] = Field(..., description="Resolved user permissions")
    session_id: str = Field(..., description="Session identifier")


class RefreshRequest(BaseModel):
    """Token refresh request model."""

    refresh_token: str | None = Field(
        None, description="Refresh token (optional, prefers cookie if not provided)"
    )
    device_info: DeviceInfo | None = Field(
        None, description="Device information (added server-side)"
    )


class PasswordResetRequest(BaseModel):
    """Password reset request model."""

    email: EmailStr = Field(..., description="User email address")


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation model."""

    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")


__all__ = [
    "ChangePasswordRequest",
    "LoginRequest",
    "LoginResponse",
    "PasswordResetConfirm",
    "PasswordResetRequest",
    "ProfileUpdate",
    "RefreshRequest",
    "RegisterRequest",
    "TokenPair",
    "TokenPayload",
]
