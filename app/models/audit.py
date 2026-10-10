"""Security audit events as the API returns them."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    """One security-relevant change."""

    id: str
    at: datetime = Field(..., description="When the change happened (UTC)")
    action: str = Field(..., description="What happened, e.g. rbac.role_assigned")
    actor_id: str | None = Field(None, description="Who did it; None for unauthenticated flows")
    target_type: str = Field(..., description="Kind of thing changed: user, session, group...")
    target_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = Field(None, description="Matches the request's log lines")
    details: dict[str, Any] = Field(default_factory=dict)


class AuditEventListResponse(BaseModel):
    """One page of audit events, newest first."""

    events: list[AuditEvent]
    total: int
    page: int
    page_size: int
    has_next: bool
