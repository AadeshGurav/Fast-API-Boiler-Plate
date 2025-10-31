"""OAuth2 models for external provider authentication."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from app.core.dynamic_config import DynamicConfig


class OAuthProvider(str, Enum):
    """OAuth provider enumeration."""

    GOOGLE = "google"
    APPLE = "apple"


class OAuthConfig(DynamicConfig):
    """OAuth provider configuration."""

    provider: OAuthProvider = Field(..., description="OAuth provider")
    client_id: str = Field(..., description="OAuth client ID")
    client_secret: str = Field(..., description="OAuth client secret")
    redirect_uri: str = Field(..., description="OAuth redirect URI")
    scopes: list[str] = Field(default_factory=list, description="OAuth scopes")
    authorization_url: str = Field(..., description="Authorization URL")
    token_url: str = Field(..., description="Token exchange URL")
    userinfo_url: str = Field(..., description="User info URL")


class OAuthToken(DynamicConfig):
    """OAuth token model."""

    access_token: str = Field(..., description="OAuth access token")
    refresh_token: str | None = Field(None, description="OAuth refresh token")
    expires_in: int = Field(..., description="Token expiration in seconds")
    token_type: str = Field(default="Bearer", description="Token type")
    scope: str | None = Field(None, description="Token scope")


class OAuthUserInfo(DynamicConfig):
    """OAuth user information model."""

    provider_user_id: str = Field(..., description="Provider user ID")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User name")
    picture: str | None = Field(None, description="User picture URL")


class OAuthAccount(DynamicConfig):
    """OAuth account link model."""

    user_id: str = Field(..., description="Local user ID")
    provider: OAuthProvider = Field(..., description="OAuth provider")
    provider_user_id: str = Field(..., description="Provider user ID")
    access_token: str = Field(..., description="OAuth access token")
    refresh_token: str | None = Field(None, description="OAuth refresh token")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Account link creation time"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update time"
    )


__all__ = [
    "OAuthProvider",
    "OAuthConfig",
    "OAuthToken",
    "OAuthUserInfo",
    "OAuthAccount",
]
