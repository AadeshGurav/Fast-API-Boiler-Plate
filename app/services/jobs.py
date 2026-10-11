"""Durable background jobs on the configured database: no broker, no extra infrastructure.

``JobService.enqueue`` writes a job record; a worker claims it with a conditional update
(``status: queued`` → ``running``), which exactly one worker wins on every backend, runs the
registered handler, and records the outcome. Failures retry with exponential backoff and
jitter; after ``jobs_max_attempts`` the job is ``dead`` and stays visible to administrators
(a dead-letter queue). A worker that dies mid-job leaves a lease that expires, and the job runs
again, so **handlers must be idempotent**.

The worker runs inside the API process by default (``jobs_run_in_api``) or on its own with
``python -m app.jobs``. See ADR 0007 for why this is not Celery, ARQ or Taskiq.
"""

from __future__ import annotations

import asyncio
import random
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from app.core.interfaces.database_interface import DuplicateRecordError
from app.services.data import cursor as keyset
from app.services.data.policies import CachePolicy

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from app.services.data import DataService
    from app.services.logger import Logger
    from config import Config

    Handler = Callable[[dict[str, Any]], Awaitable[None]]

COLLECTION = "jobs"
DB = CachePolicy.DB_ONLY
QUEUED, RUNNING, DONE, DEAD = "queued", "running", "done", "dead"
MAX_ERROR_LENGTH = 500


class JobService:
    """Enqueue jobs, run them, and let administrators inspect and retry them."""

    def __init__(self, config: Config, logger: Logger, data_service: DataService) -> None:
        self.logger = logger
        self.data_service = data_service
        self.handlers: dict[str, Handler] = {}
        self.max_attempts: int = config["jobs_max_attempts"]
        self.timeout: float = config["jobs_timeout_seconds"]
        self.lease = timedelta(seconds=config["jobs_timeout_seconds"] * 2)
        self.poll_seconds: float = config["jobs_poll_seconds"]
        self.batch: int = config["jobs_batch_size"]
        self.backoff_base: float = config["jobs_retry_base_seconds"]
        self.worker_id = uuid.uuid4().hex[:12]

    # ---- producing ---------------------------------------------------------------------
    def handler(self, name: str) -> Callable[[Handler], Handler]:
        """Register the coroutine that runs jobs called ``name``::

        @services.job_service.handler("reports.build")
        async def build_report(payload): ...
        """

        def register(fn: Handler) -> Handler:
            if name in self.handlers:
                raise ValueError(f"A handler for job {name!r} is already registered")
            self.handlers[name] = fn
            return fn

        return register

    async def enqueue(
        self,
        name: str,
        payload: dict[str, Any] | None = None,
        *,
        run_at: datetime | None = None,
        idempotency_key: str | None = None,
    ) -> str:
        """Queue a job; returns its id. With ``idempotency_key``, enqueuing the same key again
        returns the first job's id instead of queuing a duplicate.

        Payloads are stored as plain records: never put secrets in them.
        """
        now = datetime.now(UTC)
        job = {
            "id": uuid.uuid4().hex,
            "name": name,
            "payload": payload or {},
            "status": QUEUED,
            "attempts": 0,
            "run_at": run_at or now,
            "created_at": now,
            "updated_at": now,
            "lease_until": None,
            "last_error": None,
            "finished_at": None,
        }
        if idempotency_key is not None:
            job["idempotency_key"] = idempotency_key
        try:
            await self.data_service.insert(COLLECTION, job)
        except DuplicateRecordError:
            existing = await self.data_service.get(
                COLLECTION, {"idempotency_key": idempotency_key}, policy=DB
            )
            if existing is None:  # deleted between the two calls: rare, and safe to surface
                raise
            return existing["id"]
        return job["id"]

    # ---- consuming ---------------------------------------------------------------------
    async def run_once(self) -> int:
        """Requeue expired leases, then claim and run up to ``jobs_batch_size`` due jobs.
        Returns how many jobs this call ran."""
        now = datetime.now(UTC)
        await self.data_service.update_many(
            COLLECTION,
            {"status": RUNNING, "lease_until": {"$lt": now}},
            {"status": QUEUED, "lease_until": None, "updated_at": now},
        )
        due = await self.data_service.find_many(
            COLLECTION,
            {"status": QUEUED, "run_at": {"$lte": now}},
            policy=DB,
            sort=[("run_at", 1)],
            limit=self.batch,
        )
        ran = 0
        for job in due:
            if await self._claim(job):
                await self._run(job)
                ran += 1
        return ran

    async def run_forever(self) -> None:
        """Poll until cancelled. A failed pass is logged and the loop carries on."""
        self.logger.info(f"Job worker {self.worker_id} started ({sorted(self.handlers)})")
        while True:
            try:
                ran = await self.run_once()
            except Exception as e:
                self.logger.error(f"Job worker pass failed: {e}")
                ran = 0
            if not ran:  # drain a backlog without waiting; sleep only when idle
                await asyncio.sleep(self.poll_seconds)

    async def _claim(self, job: dict[str, Any]) -> bool:
        now = datetime.now(UTC)
        job["attempts"] = job.get("attempts", 0) + 1
        if job["attempts"] > self.max_attempts:
            # Only reachable through expired leases: the job keeps killing its worker.
            await self.data_service.update(
                COLLECTION,
                {"id": job["id"], "status": QUEUED},
                {
                    "status": DEAD,
                    "finished_at": now,
                    "updated_at": now,
                    "last_error": "Worker stopped during every attempt (lease expired)",
                },
                policy=DB,
            )
            return False
        return await self.data_service.update(
            COLLECTION,
            {"id": job["id"], "status": QUEUED},
            {
                "status": RUNNING,
                "attempts": job["attempts"],
                "lease_until": now + self.lease,
                "worker": self.worker_id,
                "updated_at": now,
            },
            policy=DB,
        )

    async def _run(self, job: dict[str, Any]) -> None:
        handler = self.handlers.get(job["name"])
        extra = {"service": "JobService", "job_id": job["id"], "job": job["name"]}
        try:
            if handler is None:
                raise LookupError(f"No handler registered for job {job['name']!r}")
            await asyncio.wait_for(handler(job.get("payload") or {}), timeout=self.timeout)
        except Exception as e:
            await self._failed(job, e, permanent=isinstance(e, LookupError))
            self.logger.warning(f"Job failed (attempt {job['attempts']}): {e!r}", extra=extra)
            return
        now = datetime.now(UTC)
        await self._finish(job, {"status": DONE, "finished_at": now, "last_error": None})
        self.logger.info("Job done", extra=extra)

    async def _failed(self, job: dict[str, Any], error: Exception, *, permanent: bool) -> None:
        now = datetime.now(UTC)
        message = f"{type(error).__name__}: {error}"[:MAX_ERROR_LENGTH]
        if permanent or job["attempts"] >= self.max_attempts:
            await self._finish(job, {"status": DEAD, "finished_at": now, "last_error": message})
            return
        # Exponential backoff with full jitter, so retries of a shared outage spread out.
        delay = random.uniform(0, self.backoff_base * 2 ** (job["attempts"] - 1))  # noqa: S311
        await self._finish(
            job,
            {"status": QUEUED, "run_at": now + timedelta(seconds=delay), "last_error": message},
        )

    async def _finish(self, job: dict[str, Any], fields: dict[str, Any]) -> None:
        # Conditional on our claim: if the lease expired and another worker took the job,
        # this stale outcome is dropped instead of overwriting the newer run.
        await self.data_service.update(
            COLLECTION,
            {"id": job["id"], "status": RUNNING, "worker": self.worker_id},
            {**fields, "lease_until": None, "updated_at": datetime.now(UTC)},
            policy=DB,
        )

    # ---- administration ------------------------------------------------------------------
    async def list_jobs(
        self,
        *,
        status: str | None,
        name: str | None,
        page: int,
        page_size: int,
        cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], int, str | None]:
        filters = {k: v for k, v in {"status": status, "name": name}.items() if v is not None}
        query = {"$and": [filters, keyset.after(cursor, "created_at", "id")]} if cursor else filters
        rows = await self.data_service.find_many(
            COLLECTION,
            query,
            policy=DB,
            sort=keyset.newest_first("created_at", "id"),
            skip=0 if cursor else (page - 1) * page_size,
            limit=page_size + 1,
        )
        jobs = rows[:page_size]
        next_cursor = keyset.encode(jobs[-1], "created_at", "id") if len(rows) > page_size else None
        return jobs, await self.data_service.count(COLLECTION, filters), next_cursor

    async def retry(self, job_id: str) -> bool:
        """Queue a dead job again from scratch; False if there is no such dead job."""
        now = datetime.now(UTC)
        return await self.data_service.update(
            COLLECTION,
            {"id": job_id, "status": DEAD},
            {
                "status": QUEUED,
                "attempts": 0,
                "run_at": now,
                "finished_at": None,
                "updated_at": now,
            },
            policy=DB,
        )
