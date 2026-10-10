# Changelog

All notable changes are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). The running version is
`app_version` in `app/settings.py`.

## [Unreleased]

### Added

- Engineering standards (`docs/STANDARDS.md`), binding for every pull request, human or AI.
- Bring-your-own backend guide (`docs/how-to/write-a-backend.md`): the database, cache and
  storage contracts, including the filter vocabulary.
- Committed code knowledge graph (`graphify-out/`), rebuilt on every push to `develop`;
  `make hooks` refreshes it after each local commit. `AGENTS.md` and `CLAUDE.md` point AI agents
  to it.
- Competitive analysis and roadmap (`docs/proposals/2026-10-competitive-analysis.md`).
- CI: tests on Python 3.11 and 3.13 with a coverage report, a `pip-audit` job for known
  vulnerabilities in pinned dependencies, and a job that builds the Docker image and fails on
  HIGH or CRITICAL fixable vulnerabilities (Trivy).
- Backend contract suite (`tests/contract/`): the same database and cache tests run against the
  in-memory stand-ins by default, and against real MongoDB and Redis in CI. Backend authors run
  it against their own class (`CONTRACT_DATABASES`, `CONTRACT_CACHES`).
- The OpenAPI contract is committed as `docs/reference/openapi.json` (`make openapi`), and a
  test fails when it drifts from the application. Operation ids are the route function names,
  so generated clients get stable method names; see `docs/how-to/generate-a-client.md`.

### Changed

- Unique-index violations surface as `DuplicateRecordError` from every database backend
  instead of a driver exception; `FakeDatabase` now enforces declared unique indexes.
- OpenAPI `operationId`s changed from FastAPI's generated `<name>_<path>_<method>` to the route
  function name. Regenerate any client built from the old schema.
- ods spreadsheets are read and written with `odfpy` directly; pandas and numpy (about 110 MB)
  are no longer dependencies. Repeated empty rows and columns no longer count against the
  cell cap, and expanding a hostile file past the cap is refused before allocation.

### Fixed

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
