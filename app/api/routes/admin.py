"""Administration: the security audit log. Everything under ``/admin`` needs ``*``."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_audit_service
from app.models.audit import AuditEvent, AuditEventListResponse
from app.services.audit import AuditService

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.get("/audit-events", response_model=AuditEventListResponse)
async def list_audit_events(
    actor_id: str | None = Query(None, description="Only changes made by this user"),
    target_type: str | None = Query(None, description="user, session, group..."),
    target_id: str | None = Query(None, description="Only changes to this record"),
    action: str | None = Query(None, description="e.g. user.password_changed"),
    since: datetime | None = Query(None, description="Only events after this time"),
    until: datetime | None = Query(None, description="Only events before this time"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    audit_service: AuditService = Depends(get_audit_service),
) -> AuditEventListResponse:
    """Who changed what, newest first."""
    events, total = await audit_service.list_events(
        actor_id=actor_id,
        target_type=target_type,
        target_id=target_id,
        action=action,
        since=since,
        until=until,
        page=page,
        page_size=page_size,
    )
    return AuditEventListResponse(
        events=[AuditEvent(**event) for event in events],
        total=total,
        page=page,
        page_size=page_size,
        has_next=page * page_size < total,
    )
