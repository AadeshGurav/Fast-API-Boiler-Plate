"""OAuth2 models for external provider authentication."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class OAuthUserInfo(BaseModel):
    """OAuth user information model."""

    provider_user_id: str = Field(..., description="Provider user ID")
    email: str | None = Field(None, description="User email, if the provider shares it")
    name: str = Field(..., description="User name")
    picture: str | None = Field(None, description="User picture URL")
    email_verified: bool = Field(
        default=False, description="Provider vouches that the user owns this email"
    )


class OAuthAccount(BaseModel):
    """OAuth account link model."""

    user_id: str = Field(..., description="Local user ID")
    provider: str = Field(..., description="Provider name from oauth_providers")
    provider_user_id: str = Field(..., description="Provider user ID")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Account link creation time"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last update time"
    )


__all__ = [
    "OAuthAccount",
    "OAuthUserInfo",
]
