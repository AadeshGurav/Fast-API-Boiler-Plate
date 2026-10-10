# Architecture

## Shape

One deployable unit (a modular monolith): FastAPI app → services → data layer → MongoDB/Redis.

```
request ─► request-id ─► security headers ─► CORS ─► body-size limit ─► Sentry ─► error handler
        ─► timeout/concurrency cap ─► rate limiter ─► session-cookie writer ─► RBAC ─► route
```

Starlette runs the *last added* middleware first; `AppFactory.__setup_middleware` documents
and registers the list innermost-first. Ordering is deliberate: CORS and security headers wrap
everything that can reject a request, so 401/403/429 responses carry them; the error handler
wraps the rest so nothing escapes as a bare 500.

## Wiring

No DI framework and no globals. `build_services(config)` (`app/services/registry.py`)
constructs every service with ordinary constructors, in dependency order, and returns a
`Services` dataclass. `create_app()` (`app/api/app.py`, run with `uvicorn --factory`) stores it
on `app.state.services`; routes receive services through `app/api/deps.py`. Tests call
`create_app(config)` and get an isolated application.

## Layers

| Layer | Responsibility | Must not |
| --- | --- | --- |
| `database/*`, `cache/*`, `services/file/storage/*` | One engine each, behind an interface | Know collections, users or caching |
| `DatabaseService` / `CacheService` | Select the backend, namespace keys, log failures | Seed data, log payloads |
| `DataService` | Cache-aware `get/set/update/delete/insert/increment` | Hold domain rules |
| `services/data/*_ops.py` | Per-collection operations and their cache keys | Reach past `DataService` |
| `services/*` | Business rules (auth, RBAC, files) | Touch Mongo/Redis directly |
| `routes/*` | HTTP: parse, call a service, shape the response | Contain business logic |

### Bring your own backend

Cache, database and file storage are interfaces with built-in implementations
(`redis`/`memory`, `mongodb`, `local`). Set `app_cache_provider`, `app_database_provider` or
`file_storage_backend` to `package.module:YourClass`; the class implements
`CacheInterface` / `DatabaseInterface` / `StorageInterface` and is constructed with
`(config, logger)`. Rate limiting is a cache operation (`hit`), so any cache backend works.

### Rules worth knowing

* `set()` is an **upsert**; `update()` never creates a record. Use `update()` for edits.
* Writes invalidate cache entries instead of caching the written fragment. Records cached under
  several keys (users: id/username/email) are invalidated through their ops class.
* Security decisions (login, file ownership) read the database, not the cache.
* Indexes are declared in `services/data/schema.py`; one-off changes are versioned
  migrations in `services/data/migrations.py` (recorded in `schema_migrations`).

## RBAC

Definitions (roles, groups, inheritance) are configuration (`[rbac_roles.*]` / `[rbac_groups.*]` in
`config.toml`), loaded into memory; the list of permissions is derived from the roles. A user's roles/groups live on the user record; temporary grants in the
`temporary_permissions` collection. Effective permissions are resolved from those and cached per
user, invalidated when any input changes. `*` grants everything, `resource:*` a whole resource.

## Observability (all optional, off by default)

`metrics_service` (Prometheus, private registry, route-template labels), `tracing_service`
(OpenTelemetry SDK + official instrumentation, OTLP export) and `sentry_service` (SDK
integrations). Logging is stdlib: console plus JSON lines in `logs/app.log` through a queue.

## Authentication model

* **Access token** (15 min) and **refresh token** (7 or 30 days) are JWTs carrying a session
  id (`sid`). A token works only while its session exists, is unrevoked and unexpired, so
  logout, "log out everywhere", password reset and refresh-token reuse take effect at once.
* **Refresh rotation:** each refresh issues a new pair and stores the new refresh-token hash.
  Presenting an already-rotated token (outside a short grace window for parallel tabs) revokes
  the session: it means the token leaked.
* **Cookies** are HttpOnly + Secure (Secure off only in debug); `Authorization: Bearer` also
  works. If the access token is missing/expired and a valid refresh cookie exists, the request
  is refreshed transparently and new cookies are written on the response.
* **Lockout:** an atomic failure counter locks an account for 15 minutes after 5 failures.
  Every outcome is logged to `login_attempts` (90-day TTL). Unknown users, wrong passwords and
  locked accounts get the same response and take the same time.

## Authorization

`RBACMiddleware` authenticates every non-public path and requires:
`*` on `admin_only_paths`, otherwise `<resource>:<action>` where resource is the first path
segment after `/api/v1/` and action comes from the HTTP method (`read`/`write`/`delete`).
Roles live in `config.toml`; a test fails
if a normal user cannot be granted the permissions the existing routes require.

## Files

A file has a `file_id` and numbered versions (one record each, immutable bytes). Uploads and
spreadsheet edits add versions. Everything is scoped to the owner; other users get 404.
Chunked uploads stage chunks on the storage backend under `_uploads/<user>/<upload_id>/` with
the session record in the cache, keyed by user so ids cannot be shared or hijacked.
Request bodies are capped by `BodySizeLimitMiddleware` before they are buffered. File bytes
are streamed end to end (upload -> hash/limit -> storage; storage -> response), so memory does
not grow with file size; a background task purges abandoned chunk staging
(`file_cleanup_interval`). Backends: `local` (one host) or `s3` (shared, S3-compatible,
multipart uploads, optional direct downloads via `file_download_redirect`).

## Known limits

* xlsx edits patch the zip package (`xlsx_package`/`xlsx_patch`): charts, images, formulas and
  styles of everything not overwritten survive. Not preserved: overwriting the anchor of a
  shared/array formula is refused, and Excel recalculates formulas on next open. ods/csv edits
  rebuild from values. The previous version is always kept.
* The default `local` storage is one host's disk. Set `file_storage_backend = "s3"`
  (`pip install -r requirements-s3.txt`, or build the image with `--build-arg INSTALL_S3=true`)
  for anything running on more than one host. Uploads to S3 pass through the API once; set
  `file_download_redirect` so downloads do not.
* `MemoryCache` is per process, so `app_workers > 1` with it is refused at startup.
* Streamed (multipart, chunked or >1 MiB) idempotent requests are compared by length, not content.
* Local accounts carry `email_verified` (set by a completed password reset or an OAuth sign-up).
  Signing in with a provider that matches an unverified local account clears that account's
  password and revokes its sessions first, so whoever registered the address cannot keep access.
* A client that stops sending its request body is cut off after `request_body_idle_timeout_seconds`
  (408). Slow-but-steady senders are still bounded only by the request timeout, so keep a reverse
  proxy with its own timeouts in front of any internet-facing deployment.
* Cookie-authenticated writes must come from an allowed origin (`csrf_origin_check`, on by default):
  `cors_origins`, localhost in debug, or the request's own host. Bearer-token requests are exempt.
* Storage is capped per user (`file_user_quota_bytes`, soft-deleted files included; a purge via
  `DELETE ...?hard_delete=true` frees it) and per file (`file_max_versions`). The quota sum reads
  up to the database result cap (10 000 versions); keep a counter on the user record if one user
  can legitimately hold more.
