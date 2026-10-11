# FastAPI Boilerplate: production-ready, storage-agnostic FastAPI starter

[![CI](https://github.com/AadeshGurav/Fast-API-Boiler-Plate/actions/workflows/ci.yml/badge.svg)](https://github.com/AadeshGurav/Fast-API-Boiler-Plate/actions/workflows/ci.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.142-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-8-47A248?logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Ruff](https://img.shields.io/badge/lint-ruff-D7FF64)](https://docs.astral.sh/ruff/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**A secure, production-ready FastAPI back end you can build a real product on today.**
Authentication with revocable sessions, role-based access control, versioned file storage,
rate limiting, safe retries and RFC 9457 errors are already done, tested and documented. You add
your product's resources; the plumbing is finished.

**Bring your own database.** Every layer above the storage engines talks to interfaces, never to
a driver, so you can move from MongoDB to PostgreSQL, Redis to another cache, or local disk to
any object store by writing one class: no application code changes. Complete MongoDB, Redis,
in-memory, local-disk and S3 implementations ship ready to use.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/diagrams/what-you-get-dark.svg">
  <img alt="What you get: your product sits on top of included accounts and access, files and data, and safety nets, running on open-source FastAPI, MongoDB, Redis and Docker." src="docs/diagrams/what-you-get.svg">
</picture>

## Why this boilerplate

- **Secure by default, not by checklist.** Session-bound JWTs that revoke instantly, refresh
  token rotation with theft detection, account lockout, CSRF and CORS checks, strict security
  headers, safe file handling, pinned by regression tests.
- **Production behaviour built in.** Rate limits, timeouts, overload shedding, idempotency
  keys, health probes, structured logs, and a cache that degrades instead of failing.
- **Zero-touch setup.** `make setup && make up && make run`: random passwords, free ports,
  no manual steps. 300+ tests run in about fifteen seconds without any database, and a contract
  suite proves the same behaviour on real MongoDB, PostgreSQL and Redis in CI.
- **Storage-agnostic architecture.** Database, cache and file storage sit behind interfaces
  (`DatabaseInterface`, `CacheInterface`, `StorageInterface`). Swap SQL for NoSQL, or one cloud
  for another, with one class and one setting; [the contract](docs/how-to/write-a-backend.md)
  is documented.
- **Small and readable.** No DI framework, no magic: plain wiring and clear layers.
- **AI-agent ready.** A committed, always-current [code graph](graphify-out/GRAPH_REPORT.md) lets
  AI assistants navigate the codebase without reading every file; [AGENTS.md](AGENTS.md) gives
  them the rules.
- **Documented for everyone.** Guides for developers, operators, designers and decision
  makers, an API and data-model reference, architecture decision records, and nineteen diagrams.

## Features

| Area | What you get |
| --- | --- |
| **Authentication** | Registration, sign-in with "remember me", Argon2id passwords, JWT access + rotating refresh tokens bound to server-side sessions, sign out of one or all devices, password change and email reset, sign-in with Google, Microsoft, Okta or any OpenID Connect provider (PKCE, verified ID tokens), two-factor sign-in (authenticator codes + recovery codes), passkeys (WebAuthn), scoped personal access tokens for scripts, HttpOnly cookies or Bearer tokens |
| **Authorization (RBAC)** | Roles with inheritance, groups, time-limited grants; deny-by-default `<resource>:<action>` permissions derived from each route; `*` and `files:*` wildcards; user administration |
| **Files** | Per-user files with version history, chunked and resumable uploads, image thumbnails, de-duplication, per-user quotas, spreadsheet read/edit (xlsx edited in place keeps charts and formulas; ods; csv), local disk or S3/MinIO/R2, streamed end to end |
| **API safety nets** | Rate limiting (sliding or fixed window, per tier), request size and idle-body limits, timeouts and concurrency cap, `Idempotency-Key` replay, CSRF origin check, CORS, CSP/HSTS headers, RFC 9457 `application/problem+json` errors |
| **Operations** | Durable background jobs with retries and a dead-letter view (no broker needed); signed outgoing webhooks (Standard Webhooks); a searchable security audit log; liveness, readiness and startup probes; JSON logs with request ids; optional Prometheus metrics, OpenTelemetry tracing and Sentry; Docker image and Compose stack |
| **Pluggable storage** | `DatabaseInterface` (MongoDB and PostgreSQL built in, both proven by the same contract suite in CI; MySQL, DynamoDB... via one class), `CacheInterface` (Redis or in-memory built in), `StorageInterface` (local disk and S3-compatible built in), selected by setting |
| **Developer experience** | Typed settings with TOML + environment layering and typo detection, versioned migrations, Makefile, Ruff, CI (tests on 3.11 and 3.13, real-engine contract tests, dependency audit, image scan), a committed OpenAPI contract for generated clients, Mailpit for local email, tests through the real middleware stack |

## Quick start

You need Python 3.11, Docker and `make`; [uv](https://docs.astral.sh/uv/) is recommended (a
locked install in seconds), and `make setup` falls back to pip without it.

```bash
git clone https://github.com/AadeshGurav/Fast-API-Boiler-Plate.git
cd Fast-API-Boiler-Plate
make setup     # venv, dependencies, .env (random passwords, free ports), config.local.toml
make up        # MongoDB + Redis in Docker (loopback only)
make run       # API on http://127.0.0.1:8000, interactive docs at /docs
make test      # 300+ tests, no services needed
```

Prefer containers for everything? `make docker-up` runs the API too. There is **no default
user**: uncomment the `bootstrap_admin_*` lines in `config.local.toml`, start once, then comment
them out. The [getting-started tutorial](docs/tutorials/getting-started.md) walks through
registering, signing in and uploading a file with `curl`.

## Use it for your application

1. **Start from it.** Clone or fork it, then set `app_title`, `app_description` and
   `app_database` in `config.toml` to your product's names.
2. **Add your domain.** A new resource (orders, projects, parts) touches five small places:
   model, data ops, optional service, routes, permissions.
   [Add a resource](docs/how-to/add-a-resource.md) has a complete, tested example.
3. **Shape access.** Define roles and groups in `config.toml`; a test fails if any route needs a
   permission no role can grant.
4. **Connect your front end.** Set `cors_origins`; browsers use the HttpOnly cookies, mobile
   apps and scripts use Bearer tokens. [For designers](docs/design/for-designers.md) maps every
   API state to a screen state.
5. **Ship it.** One image, environment-variable configuration, health probes.
   [Deploy](docs/how-to/deploy.md) has a production checklist.

Good fits: SaaS products, internal tools and admin back offices, document and spreadsheet
products, asset/inventory/product-lifecycle systems, and back ends for mobile or single-page apps.

## Tech stack

| Layer | Choice | Why |
| --- | --- | --- |
| Web framework | FastAPI 0.142 + Starlette, Uvicorn | Async, typed, automatic OpenAPI |
| Validation and settings | Pydantic 2 | One typed model for every setting and payload |
| Database | MongoDB 8 via Motor (default) or PostgreSQL 15+ via asyncpg | Flexible documents on either engine; TTL indexes for sessions and tokens; also holds background jobs |
| Cache | Redis 7 or in-memory (default; replaceable) | Sessions, permissions, rate limits, idempotency |
| Files | Local disk or S3 via boto3 | One host to start, any S3-compatible store to scale |
| Auth | PyJWT, argon2-cffi, httpx (OAuth), cryptography (two-factor secrets), stdlib TOTP | Standard, audited libraries |
| Spreadsheets | openpyxl, odfpy | Pure Python, same behaviour on every OS |
| Observability | stdlib logging, prometheus-client; OpenTelemetry and sentry-sdk as an optional install | Official SDKs, installed only when used |
| Tooling | Ruff, pytest, Docker, GitHub Actions | Fast feedback, reproducible builds |

## Project structure

```text
app/
  api/
    app.py            # application factory and middleware order
    middleware/       # request id, headers, body limit, CSRF, errors, timeout, rate limit, idempotency, RBAC
    routes/           # auth, oauth, users, rbac, sessions, files, health
  services/           # auth, rbac, files, oauth, cache, data layer, logging, metrics, tracing
    data/             # DataService, per-collection ops, indexes, migrations
  cache/ database/    # pluggable backends behind interfaces (bring your own)
  models/             # Pydantic request and response models
  settings.py         # every setting: type, default, description
config.toml           # project defaults, roles and groups
docs/                 # guides, reference, ADRs, diagrams
tests/                # 300+ tests; tests/contract/ runs on real engines too
graphify-out/         # code knowledge graph, rebuilt on every push (start here, people and AI)
```

## Documentation

Everything starts at **[docs/README.md](docs/README.md)**, organised by role:

| You are… | Start with |
| --- | --- |
| Building features | [Getting started](docs/tutorials/getting-started.md) → [Architecture](docs/ARCHITECTURE.md) → [Add a resource](docs/how-to/add-a-resource.md) → [API reference](docs/reference/api.md) |
| Bringing your own database | [Write a backend](docs/how-to/write-a-backend.md) |
| Contributing (people and AI) | [Standards](docs/STANDARDS.md) → [CONTRIBUTING](CONTRIBUTING.md) → [AGENTS.md](AGENTS.md) |
| Running it | [Deploy](docs/how-to/deploy.md) → [Configure](docs/how-to/configure.md) → [Runbook](docs/how-to/operate.md) |
| Designing screens | [For designers](docs/design/for-designers.md) |
| Reviewing security | [Security model](docs/explanation/security-model.md) |
| Deciding | [For decision makers](docs/overview/for-decision-makers.md) |

Every setting is listed in the [configuration reference](docs/CONFIGURATION.md), generated
from `app/settings.py`; the reasons behind the design are in the [ADRs](docs/adr/).

## FAQ

**Is it production-ready?** Yes for a single organisation: secure defaults, health probes,
graceful degradation, a deploy checklist and a runbook. Read the
[known limits](docs/ARCHITECTURE.md#known-limits) and the [scope](docs/overview/for-decision-makers.md#scope-what-it-leaves-to-you) first.

**Is it tied to MongoDB and Redis?** No. They are the bundled, production-grade defaults, and
PostgreSQL ships too: set `app_database_provider = "postgres"`
([configure](docs/how-to/configure.md#use-postgresql-instead-of-mongodb)).
Routes, services and the data layer depend only on interfaces, so MySQL, SQLite,
DynamoDB or any other store is one class plus `app_database_provider =
"package.module:YourDatabase"`, and the application code stays untouched. The backend
implements a small, documented [contract](docs/how-to/write-a-backend.md) (CRUD, an atomic
increment, unique indexes, and a seven-operator filter vocabulary). The same holds for the
cache and for file storage.

**Do I need Redis?** For one process, `app_cache_provider = "memory"` works. With several
workers or servers use Redis; the app refuses to start with an unsafe combination.

**Does it include a front end?** No, it is API-only by design ([ADR 0002](docs/adr/0002-api-only.md)).
Any web or mobile client works; the API serves cookies to browsers and Bearer tokens to apps.

**How do I add an endpoint?** Follow [add a resource](docs/how-to/add-a-resource.md); the
access-control middleware derives the required permission from the URL and method.

**How are errors returned?** Always as RFC 9457 problem documents with a stable `code`
([errors](docs/reference/api.md#errors)).

**Which sign-in providers are supported?** Username and password, and any OpenID Connect
provider (Google, Microsoft Entra ID, Okta, Auth0, Keycloak, GitLab...) by configuration alone.

## Contributing

Contributions are welcome, from typo fixes to new backends. Read
[CONTRIBUTING.md](CONTRIBUTING.md) for setup, conventions and the pull request checklist, and
the [Code of Conduct](CODE_OF_CONDUCT.md). Report vulnerabilities privately as described in
[SECURITY.md](SECURITY.md). Release history is in the [CHANGELOG](CHANGELOG.md).

If this saves you time, a ⭐ helps other developers find it.

## License

[MIT](LICENSE)
