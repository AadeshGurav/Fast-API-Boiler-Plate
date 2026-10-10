"""OAuth2 models for external provider authentication."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class OAuthProvider(StrEnum):
    """OAuth provider enumeration."""

    GOOGLE = "google"


class OAuthToken(BaseModel):
    """OAuth token model."""

    access_token: str = Field(..., description="OAuth access token")
    refresh_token: str | None = Field(None, description="OAuth refresh token")
    expires_in: int = Field(..., description="Token expiration in seconds")
    token_type: str = Field(default="Bearer", description="Token type")
    scope: str | None = Field(None, description="Token scope")


class OAuthUserInfo(BaseModel):
    """OAuth user information model."""

    provider_user_id: str = Field(..., description="Provider user ID")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User name")
    picture: str | None = Field(None, description="User picture URL")
    email_verified: bool = Field(
        default=False, description="Provider vouches that the user owns this email"
    )


class OAuthAccount(BaseModel):
    """OAuth account link model."""

    user_id: str = Field(..., description="Local user ID")
    provider: OAuthProvider = Field(..., description="OAuth provider")
    provider_user_id: str = Field(..., description="Provider user ID")
    access_token: str = Field(..., description="OAuth access token")
    refresh_token: str | None = Field(None, description="OAuth refresh token")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Account link creation time"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last update time"
    )


__all__ = [
    "OAuthAccount",
    "OAuthProvider",
    "OAuthToken",
    "OAuthUserInfo",
]
