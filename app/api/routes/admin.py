"""Administration: the security audit log and account recovery. Everything under ``/admin``
needs ``*``."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_audit_service, get_auth_service
from app.models.audit import AuditEvent, AuditEventListResponse
from app.services.audit import AuditService
from app.services.auth import AuthService

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


@router.delete("/users/{user_id}/mfa", status_code=status.HTTP_204_NO_CONTENT)
async def reset_user_mfa(
    user_id: str,
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """Turn off a user's two-factor sign-in after verifying their identity out of band."""
    if not await auth_service.mfa.reset(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Two-factor sign-in is not on for this user",
        )
