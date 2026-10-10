# Competitive analysis and roadmap proposal (October 2026)

Status: **proposal**, nothing here is approved. Items that add a dependency or change the
architecture need an issue and agreement first (AGENTS.md, STANDARDS §9), and the large ones
need an ADR.

## 1. Who we compete with

| Project | Stars (approx.) | Stack | What it has that we lack |
| --- | --- | --- | --- |
| [fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) | ~46k | FastAPI, SQLModel, PostgreSQL, React/TanStack, Traefik, uv | PostgreSQL, a generated TypeScript client, Playwright E2E, email templates with Mailpit for local testing, uv lockfile, agent skills (`.claude/skills`), one-click FastAPI Cloud deploys |
| [s3rius/FastAPI-template](https://github.com/s3rius/FastAPI-template) | ~2.8k | Generator: 5 ORMs, Postgres/MySQL/SQLite/Mongo, REST or GraphQL | A project generator (pick the DB, queue and observability you want), Taskiq/RabbitMQ/Kafka options, Alembic |
| [benavlabs/FastAPI-boilerplate](https://github.com/benavlabs/FastAPI-boilerplate) ("Fastro") | ~2.1k | SQLAlchemy 2, Postgres, Taskiq, SQLAdmin, FastCRUD | Background workers, API keys, an admin panel, `@cache` decorator, a CLI that generates deploy files, Alembic, per-tier rate limits (we have tiers too) |
| [fastapi-practices/fastapi_best_architecture](https://github.com/fastapi-practices/fastapi_best_architecture) | ~2.6k | SQLAlchemy, Celery, Casbin, MySQL/Postgres | Celery, Casbin-based permissions, plugin system |
| [fastapi-tenancy](https://fastapi-tenancy.readthedocs.io) (library) | n/a | Postgres schemas/RLS | Multi-tenancy, a structured audit-log model |

**What we have that most of them lack** (keep it and market it): session-bound tokens that
revoke instantly, refresh-token reuse detection, `Idempotency-Key` replay, RFC 9457 errors
everywhere, timeouts and load shedding, a cache that degrades instead of failing, versioned
files with streaming, interfaces in front of every storage engine, role-based docs and ADRs, and
an always-current code graph for AI agents. No competitor above has idempotency or problem+json
built in.

**What the community asks for.** Reddit and Hacker News block our research tools, so this
section rests on GitHub discussions, competitor issue lists and blog posts, not on Reddit
threads. The same points come up again and again:

1. *PostgreSQL by default.* Every popular template uses SQL and Alembic. Our MongoDB default and
   "bring your own" claim are not backed by a second database we can show.
2. *Background jobs.* Every serious template ships Celery, Taskiq or ARQ. We have none.
3. *Templates are either too basic or too opinionated* ([Indie Hackers](https://www.indiehackers.com/post/who-uses-saas-templates-for-their-projects-e073b6b095),
   [Habr](https://habr.com/en/users/gyolkin/comments): "FastAPI is a microframework"). Our
   answer is that we stay small and pluggable. Nothing below should break that.
4. *Front-end integration.* People want a typed client, not hand-written fetch calls.
5. *Maintenance signals.* Readers check commit recency, CI and docs before they adopt a template.

## 2. Gaps found in our own repository while checking

These are facts from the code, not opinions:

- **The real MongoDB and Redis are never tested.** All 177 test functions run against
  in-memory stand-ins. A Motor or Redis behaviour change would reach users before CI noticed.
- **`ruff` is unpinned** in `requirements-dev.txt`, so lint results drift between machines and
  CI. This breaks STANDARDS §9 (pin everything).
- **pandas (73 MB) and numpy (36 MB) are installed only to read and write ODS files**
  (`spreadsheet_processor.py:152,184`), and `odfpy` is already a dependency.
- **Optional observability is always installed:** 9 OpenTelemetry packages plus `sentry-sdk`
  sit in the base `requirements.txt`, while S3 already follows the right pattern
  (`requirements-s3.txt` behind a Docker build argument).
- **The audit log covers sign-ins only** (`login_attempts`). Role changes, grants, user
  administration and password changes leave no trace. The scope doc already lists this.
- **Pagination is offset-based** (`users.py:38`, `files/manage.py:39`). That matches our own
  STANDARDS §4 but degrades on large file lists.
- **CI** runs one Python version, no dependency vulnerability scan, no image build or scan, no
  coverage figure and no OpenAPI drift check.

## 3. Recommendations

Ordered by value for effort. Each item gives **what**, **why**, **how**, **tests** and **done
when**. P0 = do now, P1 = next, P2 = after that, P3 = only on demand.

---

### P0-1. Pin `ruff` and add the hygiene CI jobs

**Why.** An unpinned linter breaks STANDARDS §9 and can make a green PR fail later. Vulnerability
scans are the cheapest security control there is, and readers judge a template partly by its CI
badges.

**How.**
1. `requirements-dev.txt`: `ruff==<current version>`. Point `.pre-commit-config.yaml` at the same version.
2. `ci.yml`: add a `pip-audit -r requirements.txt` step (a dev-only tool, pinned).
3. Add a `docker` job: `docker build .`, then scan the image with Trivy (`aquasecurity/trivy-action`,
   pinned by SHA) and fail on HIGH or CRITICAL findings.
4. Add a test matrix for Python `3.11` and `3.13`, keeping `.python-version` at 3.11 until P2-3.
5. Report coverage with `pytest --cov` (`pytest-cov`, dev only) and show it in CI without a hard
   gate at first.

**Done when** CI has the new jobs, all green, and the CHANGELOG mentions them.

---

### P0-2. Remove pandas and numpy (use odfpy directly)

**Why.** pandas and numpy add about 110 MB to the image and install, plus their CVE surface and
upgrade churn, all for one niche format. `odfpy` already does the real work underneath pandas.

**How.**
1. In `SpreadsheetProcessor`, replace `pandas.read_excel(engine="odf")` with
   `odf.opendocument.load` → iterate `table:table` → `table:table-row` → `table:table-cell`,
   honouring `number-columns-repeated` and `number-rows-repeated` (capped, so a sheet that
   "repeats" a million empty rows cannot blow up memory).
2. Replace `pandas.ExcelWriter(engine="odf")` with `odf.opendocument.OpenDocumentSpreadsheet`,
   writing one `Table` per sheet, with numeric cells as `valuetype="float"` and the rest as strings.
3. Remove `pandas` from `requirements.txt` and update the ADR 0003 note.

**Tests.** Round-trip tests for ODS (read the existing fixtures, write, read again), a test for
repeated rows and columns, and a test for the cap. Existing tests must pass unchanged.

**Done when** `pip install -r requirements.txt` pulls in no numpy and the image is roughly
100 MB smaller (measure it before and after, and record both numbers in the PR).

---

### P0-3. Run the backend contract tests against real engines

**Why.** The storage-agnostic promise is our headline, but no test runs it against a real
engine. It is also a prerequisite for P1-1 (PostgreSQL) and lets people who write their own
backend prove it works.

**How.**
1. Move the backend-level assertions in `tests/test_data_layer.py` (CRUD, upsert semantics,
   atomic `increment_field`, unique-index violations, every operator in the filter vocabulary,
   `update_many` counts) into `tests/contract/test_database_contract.py`, parametrised over a
   `database` fixture.
2. The fixture yields `FakeDatabase` by default, and real `MongoDB` when `FABP_TEST_MONGO_URL` is
   set. Do the same for the cache (`MemoryCache`, plus `RedisCache` when `FABP_TEST_REDIS_URL`
   is set) and for storage (local always, S3 through moto, as today).
3. Add a CI job with `services: mongo:8, redis:7` that sets those variables and runs
   `pytest tests/contract`.
4. In `write-a-backend.md`, tell backend authors to run the suite against their class
   (`FABP_TEST_DATABASE=package.module:Class`).

**Done when** the contract suite passes on the fake and on the real engines in CI, and a
deliberately broken fake (for example, non-atomic increment) fails it.

---

### P1-1. PostgreSQL backend (built in, optional)

**Why.** It is the most common request and the stack every competitor uses. It turns "bring your
own database" from a claim into a demonstration. It also opens the door to the many teams that
do not run MongoDB at all.

**Design (needs an ADR, 0006).** Keep our document-shaped `DatabaseInterface` unchanged and
store each collection as a table `(id text primary key, doc jsonb not null)`:

| Interface need | PostgreSQL mapping |
| --- | --- |
| Filters (`$eq`, `$in`, `$gt`...) | `doc->>'field'` comparisons, with `jsonb_typeof` and numeric/timestamp casts |
| Unique / TTL indexes from `schema.py` | Expression unique indexes on `(doc->>'field')`. TTL becomes a periodic `DELETE ... WHERE (doc->>'expires_at')::timestamptz < now()` run by the existing janitor |
| `increment_field` (atomic) | `UPDATE ... SET doc = jsonb_set(doc, '{f}', to_jsonb((doc->>'f')::bigint + $1)) RETURNING` |
| `upsert_record` | `INSERT ... ON CONFLICT DO UPDATE` |

*Rejected alternatives (they go in the ADR):* SQLAlchemy ORM models per collection (doubles
every model and adds Alembic; that belongs to a user who wants relational modelling, which our
interface already allows them to add), and SQLModel (same, plus a second model layer next to
Pydantic).

**How.**
1. Add the `asyncpg` dependency in `requirements-postgres.txt` (needs issue agreement) and an
   `INSTALL_POSTGRES` Docker argument.
2. Write `app/database/postgres.py` implementing `DatabaseInterface`, with a pool and statement
   timeouts from settings (`postgres_*` fields in `app/settings.py`, then `make config-docs`).
3. Register the built-in name `postgres` in `app/core/plugins.py`.
4. Add a `postgres` profile to `docker-compose.yml`, plus a `make up-postgres` target.
5. Run the P0-3 contract suite against Postgres in CI.
6. Docs: the README FAQ, `write-a-backend.md` (now with a second reference implementation),
   `deploy.md` and the CHANGELOG.

**Done when** the whole contract suite and a smoke run of the main test suite pass with
`app_database_provider = "postgres"`, and switching providers requires no application code change.

---

### P1-2. Durable background jobs, with no new dependency

**Why.** It is the second-biggest gap. Today, password-reset email is sent inside the request,
and users have nowhere to put work such as thumbnails for big files, outgoing webhooks or
reports. STANDARDS §3 asks for the outbox pattern whenever we publish events.

**Design (ADR 0007).** Keep jobs in a `jobs` collection behind our own `DatabaseInterface`, so
they work on MongoDB, PostgreSQL or any custom backend:

- `JobService.enqueue(name, payload, run_at=None, idempotency_key=None)` inserts
  `{status: "queued", attempts: 0, run_at}`. It can be called right next to the business write.
  Atomicity across the two writes depends on the backend (a transaction on Postgres, best-effort
  on single-document MongoDB), and the ADR states that.
- A worker claims a job with `update_record({id, status: "queued"}, {status: "running", lease_until})`.
  A `True` return means this worker owns it, which is atomic on every backend. Failures retry
  with exponential backoff and jitter up to `jobs_max_attempts`, then the job moves to
  `status: "dead"` and stays visible through an admin endpoint (a dead-letter queue, STANDARDS §3).
  Expired leases are re-queued.
- Handlers are registered with `@jobs.handler("send_email")`.
- The worker runs inside the API lifespan by default (one deployable unit), or on its own with
  `python -m app.jobs` and `jobs_run_in_api = false` when you scale out.

*Rejected:* Taskiq or ARQ (an extra broker process and dependency, and ARQ is Redis-only, which
contradicts our storage-agnostic design; mention Taskiq as the upgrade path for high throughput),
Celery (sync-first), and FastAPI `BackgroundTasks` (lost on restart).

**How.** `app/services/jobs.py` (about 150 lines), indexes in `schema.py`, settings, built in
`registry.py`, `GET /api/v1/admin/jobs` (paged, `jobs:read`, admin only), and moving the
password-reset email onto the queue as the first real user.

**Tests.** Claim races (two workers, one wins), retry and backoff, dead-lettering, lease expiry,
and a job lost mid-run that runs again. Every handler must be idempotent; the docs say so.

---

### P1-3. MFA: TOTP plus recovery codes

**Why.** It is listed as missing in our own scope doc, expected by any business customer and
cheap with the standard library. Passkeys are stronger (TOTP can be phished) but cost a
dependency, so they come later (P2-4).

**How.**
1. Implement TOTP with the standard library (RFC 6238: `hmac`, `hashlib`, `struct`, `base32`;
   about 25 lines), with ±1 step tolerance. Store the last accepted step and reject reuse.
2. Routes: `POST /auth/mfa/totp` (start setup; returns the secret and `otpauth://` URI, and the
   client draws the QR code), `POST /auth/mfa/totp/confirm`, `DELETE /auth/mfa/totp` (needs the
   password plus a code), and `POST /auth/mfa/recovery-codes` (10 single-use codes, stored hashed).
3. Sign-in: when MFA is on, the password step returns `401` problem `mfa_required` with a
   short-lived `mfa_token`, bound to the user and good for 5 minutes. `POST /auth/login/mfa`
   exchanges token plus code for the normal session. The lockout counter covers MFA failures too.
4. The secret is encrypted at rest with a key from settings (`mfa_encryption_key`), using
   `cryptography`'s Fernet. This is a new runtime dependency: today only `moto`, in the test
   requirements, pulls it in. The secret is never logged.

**Tests.** RFC 6238 test vectors, replay rejection, clock skew, recovery-code single use,
lockout, and an MFA-enabled user who cannot get a session with the password alone.

---

### P1-4. Personal access tokens / API keys

**Why.** Scripts, CI and integrations need credentials that do not expire every 15 minutes and
that the user can revoke. benavlabs ships API keys.

**How.**
1. A `api_tokens` collection: `{id, user_id, name, prefix, hash, scopes, expires_at, last_used_at}`.
   The token looks like `fabp_pat_<random>`. It is shown once and stored as its `hash_token`
   value (the helper already exists).
2. `RBACMiddleware`: a Bearer value starting with `fabp_pat_` is looked up by hash
   (`CachePolicy.DB_ONLY`). Effective permissions are the user's permissions intersected with
   the token's scopes, so a token can never exceed its owner.
3. Routes `/api/v1/tokens` (create, list paged, revoke), with permissions in `config.toml`.
4. `last_used_at` is updated at most once a minute, so we don't write on every request.

**Tests.** Scope intersection, revocation takes effect immediately, expiry, a disabled user's
tokens stop working, and the token value never appears in logs or responses after creation.

---

### P1-5. Security audit log of changes

**Why.** Operators and auditors need to see who changed roles or users and when. Our scope doc
lists it as missing, and the CLAUDE.md standards (§8) require logs you can debug from.

**How.** Generalise `login_attempts` into `audit_events`
`{id, at, actor_id, action, target_type, target_id, ip, request_id, details}`, with a TTL set by
`audit_retention_days`. Services write events for: sign-in (existing), password change or reset,
MFA changes, role, group and grant changes, user disable or delete, session revocation, and token
creation or revocation. Writes never block the action (the existing pattern). Add
`GET /api/v1/audit` (paged, filterable by actor, target and action, admin only). Add a migration
that copies or retires `login_attempts`.

**Tests.** Each action writes exactly one event with the request id, a failed audit write does
not fail the action, and non-admins get 403.

---

### P1-6. OpenAPI snapshot plus a generated TypeScript client

**Why.** Our standards say the spec is the contract. A snapshot makes every contract change
visible in review. The full-stack template's generated client is one of its most praised
features, and it costs us almost nothing.

**How.**
1. Set `generate_unique_id_function` to `<tag>-<route name>` so client function names are stable.
2. Commit `docs/reference/openapi.json`, with a `make openapi` target to regenerate it.
3. A test compares `app.openapi()` to the committed file and fails with "run `make openapi`".
4. `docs/how-to/generate-a-client.md`: `npx @hey-api/openapi-ts -i docs/reference/openapi.json -o src/client`.
   No Node toolchain goes into this repo.

---

### P2-1. Schemathesis fuzzing in CI

**Why.** It finds 500s and responses that break the schema automatically, which supports our
"nothing escapes as a bare 500" promise. It runs in-process against the ASGI app, with no
server needed.

**How.** `schemathesis` as a pinned dev dependency, plus `tests/test_api_fuzz.py` using
`schemathesis.openapi.from_asgi`, with a signed-in fixture, excluding upload endpoints at first.
Mark it as a separate CI step so the main suite stays around 10 seconds.

### P2-2. Generic OpenID Connect provider

**Why.** One class that uses the discovery document covers Microsoft Entra, Okta, Auth0,
Keycloak, GitLab and others, instead of one provider class each. Business customers ask for
single sign-on with *their* identity provider.

**How.** `services/oauth/providers/oidc.py` built on the existing `OAuthProvider` base, with
PKCE, nonce, ID-token signature validation against JWKS (PyJWT's `PyJWKClient`, already
installed) and settings per configured provider. Keep the Google provider, or reimplement it on
top of this class.

### P2-3. Move to uv with a lockfile; Python 3.12+

**Why.** The two most popular competitors use uv. A lockfile with hashes protects the supply
chain, installs run 10–100× faster, and CI gets quicker. Python 3.11 reaches security-only
status; 3.13 is the current release.

**How.** Write `pyproject.toml` dependency groups (`dev`, `s3`, `postgres`, `observability`) and
`uv.lock`. `make setup` calls `uv sync`. Use a multi-stage Dockerfile (`uv sync --frozen
--no-dev` in a builder stage, then copy the venv into a slim runtime). Keep `requirements*.txt`
exported with `uv export` for people who use pip. Raise `.python-version` once the P0-1 matrix
has been green for a release. This is a workflow change, so it needs agreement first.

### P2-4. Passkeys (WebAuthn)

**Why.** They resist phishing and are where authentication is heading. They come after TOTP
because they need `webauthn` (py_webauthn), a new dependency, and more client work.

**How.** Registration and authentication ceremonies, credentials stored per user, usable as a
second factor first and as passwordless sign-in later (a setting).

### P2-5. Mailpit and file-based email templates

**Why.** Developers can see reset emails locally with no SMTP account, and email copy stops
being hard-coded strings. This serves CLAUDE.md §13 (i18n readiness).

**How.** A `mailpit` service in `docker-compose.yml` (profile `dev`), with `.env.example` SMTP
settings pointing at it. Templates go in `app/templates/email/*.txt` using `string.Template`
from the standard library, with one file per locale and an English fallback.

### P2-6. Move optional observability into an extra

**Why.** It follows the S3 pattern we already use: a smaller default install, fewer CVEs and
fewer upgrades for people who don't use OpenTelemetry or Sentry.

**How.** Create `requirements-observability.txt` (OpenTelemetry and sentry-sdk) and an
`INSTALL_OBSERVABILITY` Docker argument. Keep imports lazy (check that they are), so that
enabling tracing without the extra fails at start-up with "install
requirements-observability.txt" instead of an ImportError mid-request. `prometheus_client`
stays in the base install because it is small and `/metrics` is common.

### P2-7. Cursor pagination for unbounded collections

**Why.** Offset pagination scans and discards rows at depth, and it drifts while data changes
(CLAUDE.md §4.7). Files and the audit log can grow without bound; users rarely do.

**How.** Keep `page`/`page_size` (our standard, and fine for users). Add `cursor` plus
`next_cursor` to `GET /files` and `GET /audit`, keyed on `(created_at, id)` and opaque
(base64url). The `$gt`/`$lt` filter operators already cover it. Update STANDARDS §4 to allow
both, and document when to use which.

---

### P3 (only when a real user needs it)

- **Multi-tenancy (organisations).** It is the biggest gap for SaaS, but it touches every query
  and every permission. If it is on the roadmap at all, decide it *before* users build domain
  models on the boilerplate: add `org_id` to the records, org-scoped roles, and enforce scoping
  in `DataService` so no ops class can forget it. This needs its own ADR and your decision.
- **Outgoing webhooks.** Signed (HMAC) and delivered by P1-2 jobs with retries. Build it only
  after jobs exist.
- **A project generator (copier).** s3rius's main draw. Copier can also update existing
  projects from the template later. It is worth it once there are several optional modules
  (Postgres, jobs, spreadsheets) to choose from.
- **Project agent skills** (`.claude/skills/add-a-resource`), as the full-stack template ships.
  We already have AGENTS.md and the code graph; a skill is a small addition.

## 4. What not to add, and why

| Idea | Why not |
| --- | --- |
| Admin web panel (SQLAdmin and similar) | We are API-only by design ([ADR 0002](../adr/0002-api-only.md)). SQLAdmin is SQLAlchemy-only, so it would also break our storage-agnostic design. Point people to API clients or their own front end. |
| GraphQL | Doubles the API surface and the security review. RFC 9457, idempotency and RBAC-by-route are all REST-shaped. |
| Celery, Kafka, RabbitMQ | A second deployable piece of infrastructure before anyone needs one (CLAUDE.md §4.1 deployment simplicity). P1-2 covers the need. |
| An ORM layer (SQLAlchemy models, SQLModel) | Two model layers next to Pydantic, and it ties the core to SQL. People who want relational modelling can add it inside their own backend. |
| A bundled React front end | Out of scope (ADR 0002). The full-stack template already owns that niche, and we would lose on it. |

## 5. What to remove or reconsider

| Item | Recommendation | Why |
| --- | --- | --- |
| pandas and numpy | **Remove** (P0-2) | ~110 MB for one file format |
| OpenTelemetry and Sentry in the base install | **Move to an extra** (P2-6) | Optional features should not cost everyone |
| Unpinned `ruff` | **Pin** (P0-1) | Non-reproducible lint |
| Spreadsheet editing (`xlsx_patch`, `xlsx_package`, odfpy, openpyxl) | **Keep for now; make it an optional module when the generator lands** | No competitor has it, so it differentiates us for document products. It is also the largest piece of niche code in a general-purpose boilerplate. |
| `chore(graph)` refresh commits on `develop` | **Keep, but watch** | Bot commits to `develop` after every push can conflict with open PRs. If that happens, publish the graph as a CI artifact or rebuild it only at release time. |

## 6. Suggested order of work

Each line is one pull request, small and reviewable, with docs and CHANGELOG in the same PR:

1. P0-1 CI hygiene → 2. P0-2 drop pandas → 3. P0-3 contract suite on real engines →
4. P1-6 OpenAPI snapshot → 5. P1-5 audit log → 6. P1-3 TOTP MFA → 7. P1-4 API tokens →
8. P1-2 jobs (ADR 0007) → 9. P1-1 PostgreSQL (ADR 0006) → 10. the P2 items as demand shows.

Audit comes before MFA and tokens so that those features write audit events from day one.
Contract tests come before PostgreSQL so the new backend has a target to pass.

## 7. Decisions needed from the maintainer

1. Approve new dependencies: `asyncpg` (optional extra), `pip-audit`, `pytest-cov`,
   `schemathesis` (dev only), `cryptography` (for MFA secrets), later `webauthn`.
2. PostgreSQL design: JSONB tables (recommended, keeps one interface) or relational tables with an ORM.
3. Is multi-tenancy in scope at all? It has to be decided before 2.0, not after.
4. uv migration: yes or no (it changes the contributor workflow).

## Sources

- [fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template)
- [s3rius/FastAPI-template](https://github.com/s3rius/FastAPI-template)
- [benavlabs/FastAPI-boilerplate](https://github.com/benavlabs/FastAPI-boilerplate)
- [fastapi-practices/fastapi_best_architecture](https://github.com/fastapi-practices/fastapi_best_architecture)
- [fastapi-tenancy docs](https://fastapi-tenancy.readthedocs.io/en/latest/guides/audit-logging/)
- [FastAPI docs: generate clients](https://fastapi.tiangolo.com/advanced/generate-clients/)
- [Scalar FastAPI integration](https://scalar.com/products/api-references/integrations/fastapi)
- [Schemathesis on PyPI](https://pypi.org/project/schemathesis/)
- [WorkOS: authentication for FastAPI in 2026](https://workos.com/blog/top-authentication-solutions-fastapi-2026)
- [Leapcell: Celery vs ARQ](https://leapcell.io/blog/celery-versus-arq-choosing-the-right-task-queue-for-python-applications)
- [FastAPI discussion #9064](https://github.com/tiangolo/fastapi/discussions/9064)
- [Indie Hackers: who uses SaaS templates](https://www.indiehackers.com/post/who-uses-saas-templates-for-their-projects-e073b6b095)
