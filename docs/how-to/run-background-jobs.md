# Run background jobs

Slow or retryable work (email, webhooks, reports, imports) goes on the job queue instead of
into the request. Jobs live in the configured database, so there is nothing new to deploy
([ADR 0007](../adr/0007-background-jobs-on-the-database.md)).

## 1. Register a handler

Handlers live in one place, `register_job_handlers` in `app/services/registry.py`, so the API
and a standalone worker know the same jobs:

```python
@jobs.handler("reports.build")
async def build_report(payload: dict) -> None:
    report = await services.data_service.get("reports", {"id": payload["report_id"]})
    ...  # raise to retry; return to finish
```

**Make it idempotent.** After a crash or deploy a job can run again: check whether the work is
already done (a status field, a unique key on what you create) before doing it.

## 2. Enqueue from a service

```python
await self.job_service.enqueue("reports.build", {"report_id": report_id})
await self.job_service.enqueue("email.send", {"to": email, "subject": s, "body": b},
                               run_at=tomorrow_9am)
await self.job_service.enqueue("billing.charge", {"order_id": oid},
                               idempotency_key=f"charge:{oid}")  # queued once, however often called
```

Pass `job_service` to your service's constructor in `build_services`. Payloads are stored as
plain records: put identifiers in them, never secrets or tokens.

A built-in `email.send` job (`{to, subject, body}`) sends mail through the SMTP settings and
retries while the server is unreachable.

## 3. Choose where the worker runs

| Setup | Settings |
| --- | --- |
| Inside every API process (default) | `jobs_run_in_api = true` |
| Separate worker processes | `jobs_run_in_api = false` on the API, and run `python -m app.jobs` (as many as you like) |

In Docker Compose, add a service with the same image and `command: ["python", "-m", "app.jobs"]`.

## 4. Watch it

| Need | Do |
| --- | --- |
| See failures | `GET /api/v1/admin/jobs?status=dead` (the dead-letter queue; `last_error` says why) |
| Run a dead job again | Fix the cause, then `POST /api/v1/admin/jobs/{id}/retry` |
| Tune | `jobs_max_attempts` (5), `jobs_retry_base_seconds` (10), `jobs_timeout_seconds` (300), `jobs_poll_seconds` (2), `jobs_batch_size` (10) |

Finished jobs are deleted after `jobs_retention_days` (14).
