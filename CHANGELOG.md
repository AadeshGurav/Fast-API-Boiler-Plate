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
