"""Webhook subscriptions as administrators manage them."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class WebhookCreate(BaseModel):
    url: str = Field(..., max_length=2048, description="https URL that receives POSTs")
    events: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Event types or patterns: user.*, rbac.role_assigned, *",
    )
    description: str = Field("", max_length=200)


class Webhook(BaseModel):
    id: str
    url: str
    events: list[str]
    description: str = ""
    created_at: datetime


class WebhookCreated(Webhook):
    secret: str = Field(..., description="Signing secret (whsec_...). Shown once: store it now")
