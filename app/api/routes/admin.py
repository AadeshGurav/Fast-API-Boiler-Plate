"""Administration: the security audit log, account recovery and background jobs. Everything under ``/admin``
needs ``*``."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_audit_service, get_auth_service, get_job_service
from app.models.audit import AuditEvent, AuditEventListResponse
from app.models.job import Job, JobListResponse, JobStatus
from app.services.audit import AuditService
from app.services.auth import AuthService
from app.services.jobs import JobService

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


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    status_filter: JobStatus | None = Query(None, alias="status", description="e.g. dead"),
    name: str | None = Query(None, description="Job name, e.g. email.send"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    job_service: JobService = Depends(get_job_service),
) -> JobListResponse:
    """Background jobs, newest first. ``status=dead`` is the dead-letter queue."""
    jobs, total = await job_service.list_jobs(
        status=status_filter, name=name, page=page, page_size=page_size
    )
    return JobListResponse(
        jobs=[Job(**job) for job in jobs],
        total=total,
        page=page,
        page_size=page_size,
        has_next=page * page_size < total,
    )


@router.post("/jobs/{job_id}/retry", response_model=dict[str, str])
async def retry_job(
    job_id: str, job_service: JobService = Depends(get_job_service)
) -> dict[str, str]:
    """Queue a dead job again from its first attempt (fix the cause first)."""
    if not await job_service.retry(job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No dead job with this id"
        )
    return {"message": f"Job {job_id} queued again"}
