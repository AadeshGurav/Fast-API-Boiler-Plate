"""Session and device models for session management."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.core.dynamic_config import DynamicConfig


class DeviceInfo(DynamicConfig):
    """Device information model."""

    user_agent: str = Field(..., description="User agent string")
    ip_address: str = Field(..., description="Client IP address")
    fingerprint: str = Field(..., description="Device fingerprint")
    platform: str | None = Field(None, description="Device platform")
    os_version: str | None = Field(None, description="OS version")
    browser: str | None = Field(None, description="Browser information")
    browser_version: str | None = Field(None, description="Browser version")
    device_type: str | None = Field(None, description="Device type")
    language: str | None = Field(None, description="Language")
    is_bot: bool | None = Field(None, description="Is bot")
    geo_location: dict | None = Field(None, description="Geo location")


class RefreshToken(DynamicConfig):
    """Refresh token model."""

    token_hash: str = Field(..., description="Hashed refresh token")
    user_id: str = Field(..., description="User identifier")
    device_info: DeviceInfo = Field(..., description="Device information")
    issued_at: datetime = Field(
        default_factory=datetime.utcnow, description="Token issue time"
    )
    expires_at: datetime = Field(..., description="Token expiration time")
    last_used_at: datetime | None = Field(None, description="Last usage time")
    revoked_at: datetime | None = Field(None, description="Revocation time")


class Session(DynamicConfig):
    """Session model."""

    id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User identifier")
    refresh_token_id: str | None = Field(None, description="Associated refresh token ID")
    device_info: DeviceInfo = Field(..., description="Device information")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Session creation time"
    )
    expires_at: datetime = Field(..., description="Session expiration time")
    revoked_at: datetime | None = Field(None, description="Session revocation time")


__all__ = ["DeviceInfo", "RefreshToken", "Session"]
