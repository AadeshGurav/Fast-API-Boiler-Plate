# Changelog

All notable changes are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). The running version is
`app_version` in `app/settings.py`.

## [Unreleased]

### Added

- Cursor pagination for `/files`, `/admin/audit-events` and `/admin/jobs`: responses carry
  `next_cursor`; `?cursor=` returns the next page, fast at any depth and stable while records are
  added. Page numbers keep working.
- Outgoing webhooks (`/api/v1/admin/webhooks`): subscriptions to event types or patterns, every
  audit event published plus `WebhookService.publish()` for your own, deliveries as retried jobs,
  Standard Webhooks signatures (`webhook-id`, `webhook-timestamp`, `webhook-signature`),
  encrypted secrets, and https-only destinations that may not resolve to internal addresses.
- Passkeys (WebAuthn): register, list and remove them, and sign in without a password or
  username (`/api/v1/auth/passkeys/...`, `passkeys_enabled`, `webauthn_rp_id`,
  `webauthn_origins`). User verification is required, challenges are single-use, a lagging
  signature counter is refused as a cloned authenticator, and changes are audited. New
  dependency: `webauthn`.
- Sign-in with any OpenID Connect provider (Google, Microsoft Entra ID, Okta, Auth0, Keycloak,
  GitLab...): each `[oauth_providers.<name>]` needs only `issuer`, `client_id`, `client_secret`
  and `redirect_uri`. The flow adds PKCE (S256), a nonce, and ID-token verification against the
  provider's keys; every provider call has a timeout (`oauth_timeout_seconds`).
  `GET /api/v1/oauth/providers` lists them. Linking and unlinking are audited.
- API fuzzing (`make fuzz`, CI): Schemathesis sends generated requests to every operation and
  fails on any 5xx or undocumented status, content type or body.
- The OpenAPI contract now declares the RFC 9457 `application/problem+json` error responses
  (400, 401, 403, 404, 409, 413, 422, 429, 503) and a `ProblemDetail` schema; previously only
  success bodies and FastAPI's unused validation shape were described. Fuzzing found the gap.
- Engineering standards (`docs/STANDARDS.md`), binding for every pull request, human or AI.
- Bring-your-own backend guide (`docs/how-to/write-a-backend.md`): the database, cache and
  storage contracts, including the filter vocabulary.
- Committed code knowledge graph (`graphify-out/`), rebuilt on every push to `develop`;
  `make hooks` refreshes it after each local commit. `AGENTS.md` and `CLAUDE.md` point AI agents
  to it.
- Seven diagrams, light and dark: two-factor sign-in, API token check, audit trail, security
  data model, job lifecycle, backend contract and CI pipeline; the system context, code layers
  and data model diagrams now show PostgreSQL, jobs, audit and two-factor.
- Competitive analysis and roadmap (`docs/proposals/2026-10-competitive-analysis.md`).
- CI: tests on Python 3.11 and 3.13 with a coverage report, a `pip-audit` job for known
  vulnerabilities in pinned dependencies, and a job that builds the Docker image and fails on
  HIGH or CRITICAL fixable vulnerabilities (Trivy).
- Backend contract suite (`tests/contract/`): the same database and cache tests run against the
  in-memory stand-ins by default, and against real MongoDB and Redis in CI. Backend authors run
  it against their own class (`CONTRACT_DATABASES`, `CONTRACT_CACHES`).
- Security audit log: role, group, grant, account-status, deletion, password and session
  changes are recorded in `audit_events` with actor, IP, user agent and request id, kept for
  `audit_retention_days` (365), and searchable by administrators at `GET /api/v1/admin/audit-events`.
- Two-factor sign-in with an authenticator app (RFC 6238, standard library) and ten single-use
  recovery codes: `/api/v1/auth/mfa/*`, and `POST /api/v1/auth/login/mfa` to finish a sign-in
  that answered `401 mfa_required`. Secrets are encrypted at rest with `mfa_encryption_key`;
  each code works once; wrong codes count towards lockout. Administrators can reset a lost
  second factor (`DELETE /api/v1/admin/users/{id}/mfa`). New dependency: `cryptography`.
- Personal access tokens for scripts and integrations (`/api/v1/tokens`): `fabp_pat_...` bearer
  tokens limited by scopes and by their owner's current permissions, expiring, revocable at once,
  stored hashed. Tokens cannot manage tokens.
- PostgreSQL backend (`app_database_provider = "postgres"`, ADR 0006): one JSONB document table
  per collection, expression indexes, `FOR UPDATE` first-match writes, a time-to-live purge.
  Passes the same contract suite as MongoDB; CI runs it and an end-to-end application test
  against PostgreSQL 17. `make up-postgres`, `requirements-postgres.txt` (`asyncpg`),
  `INSTALL_POSTGRES=true` for the image.
- Durable background jobs on the configured database (`JobService`, ADR 0007): conditional
  claims, retries with exponential backoff and jitter, a `dead` state with
  `GET /api/v1/admin/jobs` and `POST /api/v1/admin/jobs/{id}/retry`, lease expiry after a crash,
  idempotency keys, a built-in `email.send` job; runs inside the API or as `python -m app.jobs`.
- The OpenAPI contract is committed as `docs/reference/openapi.json` (`make openapi`), and a
  test fails when it drifts from the application. Operation ids are the route function names,
  so generated clients get stable method names; see `docs/how-to/generate-a-client.md`.

### Upgrading

- OAuth providers: replace the explicit `authorization_url`/`token_url`/`userinfo_url` of
  `[oauth_providers.google]` with `issuer = "https://accounts.google.com"` (the explicit URLs
  still work for providers without discovery). An unknown provider now answers 404 instead of
  400, and a provider answer that fails verification 502 instead of 500.

- Add `FABP_MFA_ENCRYPTION_KEY` (32+ random characters) to an existing `.env` or deployment
  before running the app container (it refuses the placeholder). Outside containers it is
  generated into `config.secrets.toml` on first start. For PostgreSQL, also add
  `POSTGRES_PASSWORD`, `FABP_POSTGRES_PASSWORD` and `FABP_POSTGRES_PORT` (see `.env.example`), or
  delete `.env` and the dev volumes and run `make setup` again.
- The default `user` role gains `auth:delete` (turning off two-factor sign-in) and
  `tokens:read`, `tokens:write`, `tokens:delete` (personal access tokens).

### Changed

- Sentry and OpenTelemetry moved to `requirements-observability.txt` (nine packages out of the
  default install, like S3 and PostgreSQL); `INSTALL_OBSERVABILITY=true` adds them to the image.
  Enabling either without its package stops start-up with the install command.
- `make up-mail` starts Mailpit, which catches every email locally (inbox on port 8025).

- Unique-index violations surface as `DuplicateRecordError` from every database backend
  instead of a driver exception; `FakeDatabase` now enforces declared unique indexes.
- `DELETE /api/v1/sessions/all` and `DELETE /api/v1/sessions/{id}` revoke through `AuthService`,
  so they are audited like sign-out.
- OpenAPI `operationId`s changed from FastAPI's generated `<name>_<path>_<method>` to the route
  function name. Regenerate any client built from the old schema.
- ods spreadsheets are read and written with `odfpy` directly; pandas and numpy (about 110 MB)
  are no longer dependencies. Repeated empty rows and columns no longer count against the
  cell cap, and expanding a hostile file past the cap is refused before allocation.

### Fixed

- The Docker image no longer ships pip, setuptools and wheel, whose vendored copies of urllib3,
  msgpack, jaraco.context and wheel carried six HIGH vulnerabilities found by the new image scan.
- `ruff` is pinned in `requirements-dev.txt`, and the pre-commit hook uses the same version
  (it was v0.9.10 while CI installed the latest release).

## [1.0.0] - 2026-10-10

First stable release: an API-only FastAPI service on MongoDB and Redis.

### Added

- **Accounts:** registration, sign-in with "remember me", session-bound JWT access and
  refresh tokens with rotation and reuse detection, sign out of one or all devices, password
  change and email reset, profile edits, optional Google sign-in.
- **Access control:** roles, groups and inheritance in `config.toml`; temporary grants;
  deny-by-default `<resource>:<action>` permissions derived from each route; user administration.
- **Files:** per-user files with versions, chunked uploads, thumbnails, de-duplication, quotas,
  spreadsheet read and edit (xlsx edited in place), local disk or S3 storage, streamed end to end.
- **Safety nets:** rate limits per client and tier, body size and idle limits, timeouts and
  concurrency cap, `Idempotency-Key` replay, CSRF origin check, CORS, security headers,
  RFC 9457 problem responses.
- **Operations:** liveness, readiness and startup probes; JSON logs with request ids; optional
  Prometheus metrics, OpenTelemetry tracing and Sentry; a cache that degrades instead of failing.
- **Developer experience:** typed settings with TOML and `FABP_*` environment layering, pluggable
  cache/database/storage backends, versioned migrations, `make setup/up/run/test`, Docker image,
  CI, 197 tests that need no running services.
- **Documentation:** role-based guides, API and data-model reference, ADRs, and twelve
  light/dark diagrams.

### Upgrading from 0.x

The 0.x line (demo web UI, `config.d/*.json`, a dependency-injection container) is not
compatible. Move configuration into `config.local.toml` or `FABP_*` variables and run
`python -m app.settings check`; set `FABP_JWT_SECRET`; create the first admin with the
`bootstrap_admin_*` settings; copy role and group definitions into `config.toml`. Tokens issued
by 0.x stop working, and migrations 1 and 2 run once on first start.

[Unreleased]: https://github.com/AadeshGurav/Fast-API-Boiler-Plate/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/AadeshGurav/Fast-API-Boiler-Plate/releases/tag/v1.0.0
