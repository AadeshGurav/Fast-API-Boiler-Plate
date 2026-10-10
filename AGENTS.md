# AGENTS.md

Instructions for AI coding agents (Claude Code, Codex, Copilot, Cursor, ...) working in this
repository. Humans: see [CONTRIBUTING.md](CONTRIBUTING.md), which says the same at more length.

## What this is

A production-ready, API-only FastAPI service on MongoDB and Redis: authentication with
session-bound JWTs, RBAC, versioned file storage (local or S3), rate limiting, idempotency,
RFC 9457 errors. Python 3.11. Start at [docs/README.md](docs/README.md) and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Commands

```bash
make setup        # create .venv, install, write .env and config.local.toml
make test         # pytest, 197 tests, no services needed (~10 s)
make lint         # ruff check + format check (CI runs this)
make fmt          # ruff fix + format
make config-docs  # regenerate docs/CONFIGURATION.md after changing app/settings.py
make up / make run  # Docker MongoDB + Redis, then the API
```

Run `make fmt && make lint && make test` before finishing any change.

## Where things go

| Change | Place |
| --- | --- |
| New resource | model `app/models/`, ops `app/services/data/*_ops.py` (+ register in `DataService`, indexes in `schema.py`), routes `app/api/routes/`, include in `AppFactory.__setup_routes`, permissions in `config.toml`. Guide: docs/how-to/add-a-resource.md |
| Business rule | a service in `app/services/`, built in `services/registry.py::build_services` |
| Setting | a field with type, default, description in `app/settings.py`; read as `config["name"]` |
| Data migration | append to `app/services/data/migrations.py`; never edit a released one |
| Backend | implement `CacheInterface` / `DatabaseInterface` / `StorageInterface` |

## Rules

- Routes never contain business logic; services never touch MongoDB/Redis directly.
- Use `DataService.update` for edits (`set` is an upsert). Security decisions read with
  `CachePolicy.DB_ONLY` / `fresh=True`, never the cache.
- Client errors: raise `HTTPException`; they become problem+json. Never leak internals.
- Collection endpoints are paged (`page`, `page_size` ≤ 200, `total`, `has_next`).
- Every new route needs `<resource>:<action>` granted to some role in `config.toml`; a test
  fails otherwise.
- New logic gets tests through the real app (`env` fixture in `tests/conftest.py`), including
  failure branches; bug fixes get a regression test.
- Docs change in the same change as behaviour. Keep `CHANGELOG.md` *Unreleased* current.
- No secrets in code, tests or logs. Environment variables use the `FABP_` prefix.
- Do not add dependencies without a reason; pin them in `requirements*.txt`.
