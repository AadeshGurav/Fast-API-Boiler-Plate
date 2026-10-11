"""Administration: the audit log, account recovery, background jobs and webhooks. Everything under ``/admin``
needs ``*``."""

from __future__ import annotations

from collections.abc import Awaitable
from datetime import datetime
from typing import TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_audit_service, get_auth_service, get_job_service, get_webhook_service
from app.models.audit import AuditEvent, AuditEventListResponse
from app.models.job import Job, JobListResponse, JobStatus
from app.models.webhook import Webhook, WebhookCreate, WebhookCreated
from app.services.audit import AuditService
from app.services.auth import AuthService
from app.services.data.cursor import InvalidCursorError
from app.services.jobs import JobService
from app.services.webhooks import WebhookError, WebhookService

T = TypeVar("T")

router = APIRouter(prefix="/admin", tags=["Administration"])


async def _paged(listing: Awaitable[T]) -> T:
    """Await a cursor-aware listing, turning a forged cursor into 400 instead of 500."""
    try:
        return await listing
    except InvalidCursorError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


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
    cursor: str | None = Query(None, max_length=512, description="next_cursor; replaces page"),
    audit_service: AuditService = Depends(get_audit_service),
) -> AuditEventListResponse:
    """Who changed what, newest first."""
    events, total, next_cursor = await _paged(
        audit_service.list_events(
            actor_id=actor_id,
            target_type=target_type,
            target_id=target_id,
            action=action,
            since=since,
            until=until,
            page=page,
            page_size=page_size,
            cursor=cursor,
        )
    )
    return AuditEventListResponse(
        events=[AuditEvent(**event) for event in events],
        total=total,
        page=page,
        page_size=page_size,
        has_next=next_cursor is not None,
        next_cursor=next_cursor,
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
    cursor: str | None = Query(None, max_length=512, description="next_cursor; replaces page"),
    job_service: JobService = Depends(get_job_service),
) -> JobListResponse:
    """Background jobs, newest first. ``status=dead`` is the dead-letter queue."""
    jobs, total, next_cursor = await _paged(
        job_service.list_jobs(
            status=status_filter, name=name, page=page, page_size=page_size, cursor=cursor
        )
    )
    return JobListResponse(
        jobs=[Job(**job) for job in jobs],
        total=total,
        page=page,
        page_size=page_size,
        has_next=next_cursor is not None,
        next_cursor=next_cursor,
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


@router.post("/webhooks", response_model=WebhookCreated, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    body: WebhookCreate, webhook_service: WebhookService = Depends(get_webhook_service)
) -> WebhookCreated:
    """Subscribe a URL to events. The signing secret is in this response only."""
    try:
        secret, record = await webhook_service.create(body.url, body.events, body.description)
    except WebhookError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return WebhookCreated(secret=secret, **record)


@router.get("/webhooks", response_model=list[Webhook])
async def list_webhooks(
    webhook_service: WebhookService = Depends(get_webhook_service),
) -> list[Webhook]:
    """Every subscription (at most 50), newest first."""
    return [Webhook(**w) for w in await webhook_service.list_all()]


@router.delete("/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_webhook(
    webhook_id: str, webhook_service: WebhookService = Depends(get_webhook_service)
) -> None:
    """Unsubscribe; queued deliveries to it are dropped."""
    if not await webhook_service.remove(webhook_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")


@router.post("/webhooks/{webhook_id}/test", status_code=status.HTTP_202_ACCEPTED)
async def test_webhook(
    webhook_id: str, webhook_service: WebhookService = Depends(get_webhook_service)
) -> dict[str, str]:
    """Queue a webhook.test delivery; watch /admin/jobs for the outcome."""
    if not await webhook_service.send_test(webhook_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    return {"message": "Test delivery queued"}
