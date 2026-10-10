"""Personal access tokens as the API accepts and returns them."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ApiTokenCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="What the token is for")
    scopes: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Permissions the token is limited to, e.g. ['files:read']",
    )
    expires_in_days: int = Field(90, ge=1, description="Lifetime; at most api_token_max_days")


class ApiToken(BaseModel):
    id: str
    name: str
    prefix: str = Field(..., description="First characters, to recognise the token in a list")
    scopes: list[str]
    created_at: datetime
    expires_at: datetime
    last_used_at: datetime | None = None


class ApiTokenCreated(ApiToken):
    token: str = Field(..., description="The secret. Shown once: store it now")


class ApiTokenListResponse(BaseModel):
    tokens: list[ApiToken]
    total: int
    page: int
    page_size: int
    has_next: bool
