# fastapi_boilerplate

An API-only FastAPI service on MongoDB and Redis, built to be started in minutes and extended
without surprises: typed configuration, sessions and RBAC, per-user files, pluggable backends,
problem+json errors, and tests that need no running services.

## Quick start

```bash
make setup     # venv, dependencies, .env (random passwords, free ports), config.local.toml
make up        # MongoDB + Redis in Docker (loopback only)
make run       # API on http://127.0.0.1:8000, interactive docs at /docs (debug mode)
make test      # 137 tests, no services needed
```

Prefer containers for everything? `make docker-up` runs the API too. `make help` lists all targets.
Python 3.11.

There is **no default user**. To create the first administrator, uncomment the
`bootstrap_admin_*` lines in `config.local.toml`, start once, then remove them.

## Configuration in five minutes

Every setting is declared once, with a type, default and description, in
[`app/settings.py`](app/settings.py); the full list is generated into
[`docs/CONFIGURATION.md`](docs/CONFIGURATION.md). Sources, lowest priority first:

| Source | Use it for |
| --- | --- |
| defaults in `app/settings.py` | nothing to do |
| `config.toml` | project defaults, **roles and groups** (committed) |
| `config.local.toml` | your machine's overrides (git-ignored; `make setup` creates it) |
| `config.secrets.toml` | the generated JWT key (git-ignored) |
| `.env` | `FABP_<NAME>=value` lines (git-ignored; `make setup` creates it) |
| environment | `FABP_<NAME>=value`, e.g. `FABP_APP_PORT=9000`, `FABP_CORS_ORIGINS='["https://app.example.com"]'` |

```bash
make config                 # every effective setting and which source set it
python -m app.settings check
```

Mistakes fail at startup and say what and where, e.g.
`unknown setting 'mongo_hots' (from config.local.toml). Did you mean 'mongo_host'?`.
The committed defaults are production-safe (debug off, loopback bind, Secure cookies, strict
CSP); `config.local.toml` opts into development conveniences.

## What is in the box

| Area | Where | Notes |
| --- | --- | --- |
| Auth | `services/auth/`, `routes/auth/` | Argon2id, JWT access + rotating refresh tokens bound to a server-side session, lockout, audit log, change/reset password, profile |
| Users | `routes/users.py` | Paged list, suspend/activate, delete (permission-gated) |
| Access control | `middleware/rbac.py`, `services/rbac.py`, `config.toml` | Roles, groups, temporary grants; `<resource>:<action>` derived from the URL; `files:*` and `*` wildcards |
| Files | `services/file/`, `routes/files/` | Per-user files with versions, chunked uploads, thumbnails, spreadsheet read/edit |
| Safety nets | `middleware/` | Rate limits, request-size and time limits, concurrency cap, `Idempotency-Key` replay, CORS, security headers, request ids |
| Backends | `database/`, `cache/`, `services/file/storage/` | MongoDB, Redis or in-memory, local disk or S3; bring your own with `package.module:Class` |
| Operations | `routes/health.py`, `services/{metrics,tracing,sentry}.py` | `/api/v1/{health,live,ready,startup}`; optional Prometheus, OpenTelemetry, Sentry |

How the pieces fit: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Why they are this way:
[`docs/adr/`](docs/adr). Adding your own resource: [`docs/EXTENDING.md`](docs/EXTENDING.md).

## Development

* Tests use in-memory stand-ins for MongoDB and Redis; the end-to-end tests run the real
  middleware stack through `TestClient`. `make lint` / `make fmt` run ruff; CI runs both.
* `make graph` refreshes the code knowledge graph in `graphify-out/`.
* Optional: `pre-commit install` runs ruff before each commit.

## Operating notes

* Behind a reverse proxy set `trusted_proxy_count` so rate limits and the audit log see client
  IPs. With more than one worker use the `redis` cache (`memory` is per process).
* In containers set `FABP_JWT_SECRET`, `FABP_MONGO_PASSWORD`, `FABP_REDIS_PASSWORD` (or mount
  `config.secrets.toml`) so tokens survive restarts.
* Email for password resets: set `smtp_host` (and friends); without it the message is only logged.
* `make setup` picks free host ports, so a MongoDB already on your machine cannot shadow the
  Docker one. After regenerating `.env`, run `make reset-data` (old Docker volumes keep the old
  database password).
