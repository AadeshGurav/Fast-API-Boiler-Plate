# 0007: Background jobs live in the configured database

**Status:** accepted (2026-10-11)

**Context.** Every widely used FastAPI template ships a job runner (Celery, ARQ or Taskiq), and
applications built on this one need somewhere to put slow or retryable work: email, webhooks,
reports, imports. Our constraints: one deployable unit (CLAUDE.md §4.1), storage-agnostic
backends ([ADR 0004](0004-plain-wiring-and-pluggable-backends.md)), and failures that are
visible rather than silent (STANDARDS §3).

**Decision.** A `jobs` collection behind `DatabaseInterface`, and a `JobService` that:

* claims a job with a conditional update (`{id, status: "queued"}` → `running`), which exactly
  one worker wins on every backend (a contract test proves it);
* runs the registered handler under a time limit, holding a lease of twice that limit;
* retries failures with exponential backoff and full jitter up to `jobs_max_attempts`, then marks
  the job `dead`, where administrators can see and retry it (`/admin/jobs`);
* re-queues jobs whose lease expired (worker crash or deploy), and drops a stale worker's result
  through a write conditioned on its own claim;
* de-duplicates with an optional `idempotency_key` (a sparse unique index);
* runs inside each API process by default, or alone with `python -m app.jobs`.

**Alternatives considered.**
*Celery*: sync at heart, needs a broker and a result backend, a second deployable on day one.
*ARQ*: asyncio-native but Redis-only, which would make Redis mandatory and contradict the
pluggable cache. *Taskiq*: a good fit at high throughput (brokers for Redis, RabbitMQ, NATS); the
recommended upgrade path when polling the database stops being cheap. *FastAPI
`BackgroundTasks`*: in-process and lost on restart, with no retries. *A transactional outbox
proper*: our `DatabaseInterface` has no multi-record transactions, so "write the business record
and enqueue" is two writes; handlers being idempotent is what makes that safe.

**Consequences.** Handlers must be idempotent: a job can run more than once after a crash.
Polling costs one indexed query per worker per `jobs_poll_seconds` when idle. Payloads are
ordinary records, so secrets never go in them; the password-reset email therefore stays inline
(its link carries a live token, and tokens are stored only hashed). Throughput is bounded by the
database; beyond a few hundred jobs a second, move to Taskiq behind the same `enqueue` call sites.
