"""Session and device models for session management."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DeviceInfo(BaseModel):
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


__all__ = ["DeviceInfo"]
