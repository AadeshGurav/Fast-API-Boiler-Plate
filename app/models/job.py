"""Background jobs as administrators see them."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

JobStatus = Literal["queued", "running", "done", "dead"]


class Job(BaseModel):
    id: str
    name: str = Field(..., description="Which handler runs it")
    status: JobStatus
    attempts: int
    payload: dict[str, Any] = Field(default_factory=dict)
    run_at: datetime = Field(..., description="Not before this time (retries move it later)")
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None
    last_error: str | None = Field(None, description="Why the last attempt failed")
    idempotency_key: str | None = None


class JobListResponse(BaseModel):
    jobs: list[Job]
    total: int
    page: int
    page_size: int
    has_next: bool
