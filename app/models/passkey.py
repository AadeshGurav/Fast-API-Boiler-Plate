"""Passkey (WebAuthn) requests and responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PasskeyOptions(BaseModel):
    challenge_id: str = Field(..., description="Send back with the browser's answer")
    options: dict[str, Any] = Field(
        ..., description="Pass to navigator.credentials.create() / .get() (base64url fields)"
    )


class PasskeyRegistration(BaseModel):
    challenge_id: str = Field(..., max_length=64)
    name: str = Field("Passkey", min_length=1, max_length=100, description="e.g. 'MacBook'")
    credential: dict[str, Any] = Field(..., description="PublicKeyCredential as JSON")


class PasskeyLogin(BaseModel):
    challenge_id: str = Field(..., max_length=64)
    credential: dict[str, Any] = Field(..., description="PublicKeyCredential as JSON")


class Passkey(BaseModel):
    id: str
    name: str
    created_at: datetime
    last_used_at: datetime | None = None
    transports: list[str] = Field(default_factory=list)
