# API reference

Base path `/api/v1`. In debug mode the live OpenAPI UI is at `/docs` (and `/redoc`,
`/openapi.json`); it is disabled in production. The same schema is committed as
[`openapi.json`](openapi.json) and checked by a test: [generate a client](../how-to/generate-a-client.md)
from it.

## Conventions

### Authentication

Send either the access token as `Authorization: Bearer <token>`, or the HttpOnly cookies set by
login (`fastapi_boilerplate_access_token`, `fastapi_boilerplate_refresh_token`; the prefix
follows `app_title`). If the access token is missing or expired and a valid refresh cookie is
present, the request is refreshed transparently and new cookies come back on the response.
How tokens and sessions work: [security model](../explanation/security-model.md#sessions-and-tokens).

### Permissions

Every path that is not public requires `<resource>:<action>`: the resource is the first path
segment after `/api/v1/`, and the action comes from the method (`GET`/`HEAD` → `read`,
`POST`/`PUT`/`PATCH` → `write`, `DELETE` → `delete`). `/rbac` and `/metrics` require `*`
(administrators). The **Permission** column below is what each endpoint needs; the default
roles live in `config.toml`.

### Errors

Every error is an [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457) problem document with
`Content-Type: application/problem+json`:

```json
{
  "type": "about:blank",
  "title": "Forbidden",
  "status": 403,
  "detail": "Permission denied: users:read",
  "code": "app_error",
  "instance": "/api/v1/users"
}
```

| `code` | Status | Meaning |
| --- | --- | --- |
| `validation_error` | 422 | The body or query is malformed. `errors` lists `loc`, `msg`, `type` (never the submitted values). |
| `http_error` | 4xx | A client error raised by a route; `detail` says what. |
| `app_error` | 403 | Denied by the access-control middleware. |
| `rate_limited` | 429 | Over the limit; see `Retry-After`. |
| `payload_too_large` | 413 | Body above `max_request_body_bytes`. |
| `request_timeout` | 408 | The client stopped sending its body. |
| `csrf_origin_rejected` | 403 | A cookie-authenticated write from an origin that is not allowed. |
| `dependency_unavailable` | 503 | A required backend (the cache) is briefly unavailable. |
| `internal_error` | 500 | Unexpected; details only in the logs (and `developer_message` in debug). |

Responses from the idempotency layer (400, 409, 422, 503) have the same shape without `code`.
Sign-in failures are deliberately uniform: unknown user, wrong password, disabled and locked
accounts all answer `401 Invalid credentials`.

### Pagination

Collections take `page` (from 1) and `page_size` (1–200, default 50) and answer
`{ <items>, total, page, page_size, has_next }`, newest first.

### Idempotency

Any `POST`, `PUT`, `PATCH` or `DELETE` may carry `Idempotency-Key` (8–128 of `A-Z a-z 0-9 - _`).
The first request runs; a retry with the same key and body gets the stored response with
`Idempotent-Replayed: true`. Same key, different body: 422. Retry while the first is still
running: 409. Keys are scoped to the caller, method and path, and kept for
`idempotency_ttl_seconds` (24 h). Failures (5xx, 401, 403, 408, 425, 429) are not stored, so a
retry really retries.

### Response headers

`X-Request-ID` on every response (quote it in bug reports), `X-Process-Time`, and on throttled
paths `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

## Endpoints

### Health (public)

| Method | Path | Returns |
| --- | --- | --- |
| GET | `/health` | 200: up, with service name and version. |
| GET | `/live` | 200: the process answers. |
| GET | `/ready` | 200 or 503: database and cache checks, free disk. |
| GET | `/startup` | 200 or 503: backends connected. |
| GET | `/metrics` | Prometheus text. Permission `*`. |

### Authentication

| Method | Path | Permission | Purpose → success |
| --- | --- | --- | --- |
| POST | `/auth/register` | public | Create a user with the default role → 201 user |
| POST | `/auth/login` | public | `{username, password, remember_me}` → 200 user, tokens, permissions, session id; sets cookies |
| POST | `/auth/refresh` | public | Rotate the refresh token (cookie, else body) → 200 token pair; sets cookies |
| POST | `/auth/logout` | `auth:write` | End this session → 200; clears cookies |
| POST | `/auth/logout-all` | `auth:write` | End every other session → 200 `revoked_sessions` |
| POST | `/auth/change-password` | `auth:write` | `{current_password, new_password}` → 200; other sessions end |
| POST | `/auth/reset-password-request` | public | `{email}` → 200, the same answer whether or not the email exists |
| POST | `/auth/reset-password-confirm` | public | `{token, new_password}` → 200; every session ends |
| GET | `/auth/me` | `auth:read` | The signed-in user → 200 |
| PATCH | `/auth/me` | `auth:write` | `{first_name, last_name}` → 200 user |

### Sign in with a provider

| Method | Path | Permission | Purpose → success |
| --- | --- | --- | --- |
| GET | `/oauth/{provider}/authorize` | public | Redirect to the provider; sets a state cookie → 307 |
| GET | `/oauth/{provider}/callback` | public | `?code&state` → 200 like login; sets cookies |
| POST | `/oauth/{provider}/link` | `oauth:write` | Not supported yet → 501 |
| DELETE | `/oauth/{provider}/unlink` | `oauth:delete` | Remove the provider link → 200 |

Answers 503 while `oauth_enabled` is off. `provider` is `google`.

### Sessions (your own)

| Method | Path | Permission | Purpose → success |
| --- | --- | --- | --- |
| GET | `/sessions/active` | `sessions:read` | Usable sessions, `current` marked → 200 |
| GET | `/sessions/{session_id}` | `sessions:read` | One session → 200 (404 if not yours) |
| DELETE | `/sessions/{session_id}` | `sessions:delete` | Revoke one → 200 |
| DELETE | `/sessions/all` | `sessions:delete` | Revoke all, including this one → 200 `revoked_count` |

### Users (administration)

| Method | Path | Permission | Purpose → success |
| --- | --- | --- | --- |
| GET | `/users` | `users:read` | Paged accounts, `?status=` filter → 200 |
| GET | `/users/{user_id}` | `users:read` | One account → 200 |
| PATCH | `/users/{user_id}` | `users:write` | `{status}`: suspending signs out everywhere → 200. Only admins may change admins; nobody may disable themselves. |
| DELETE | `/users/{user_id}` | `users:delete` | Delete permanently (admins: `*`) → 204 |

### Access control (administrators)

All need `*`.

| Method | Path | Purpose → success |
| --- | --- | --- |
| GET | `/rbac/roles`, `/rbac/groups`, `/rbac/permissions` | Definitions from `config.toml` → 200 |
| POST | `/rbac/users/{user_id}/roles?role_id=` | Assign a role → 200 |
| DELETE | `/rbac/users/{user_id}/roles/{role_id}` | Remove a role → 200 |
| POST | `/rbac/users/{user_id}/groups?group_id=` | Add to a group → 200 |
| POST | `/rbac/temporary-permissions` | `{entity_type, entity_id, permission_id, start_time?, end_time?}`; `entity_type` is `user` or `group` → 201 id |
| DELETE | `/rbac/temporary-permissions/{id}` | Revoke early → 200 |
| GET | `/rbac/users/{user_id}/permissions` | Effective permissions → 200 |

### Files (your own)

Other users' files answer 404, never 403.

| Method | Path | Permission | Purpose → success |
| --- | --- | --- | --- |
| POST | `/files/upload` | `files:write` | Multipart `file`, optional `filename`, `tags` (comma-separated), `metadata` (JSON) → 201 file |
| POST | `/files/upload/chunk` | `files:write` | One chunk: `chunk`, `upload_id`, `chunk_number` (from 1), `total_chunks`, `total_size`, `filename` → 200 progress |
| POST | `/files/upload/chunk/complete?upload_id=` | `files:write` | Assemble → 201 file (409 if incomplete or size mismatch) |
| GET | `/files/` | `files:read` | Paged list of newest versions, `?tags=` → 200 |
| GET | `/files/{file_id}` | `files:read` | Download as attachment, `?version=` → 200 stream, or 307 to a signed URL |
| GET | `/files/{file_id}/metadata` | `files:read` | Newest version's metadata → 200 |
| GET | `/files/{file_id}/thumbnails/{size}` | `files:read` | Image thumbnail (150, 300, 600) → 200 |
| PUT | `/files/{file_id}` | `files:write` | `{filename?, tags?, metadata?}` → 200 |
| DELETE | `/files/{file_id}` | `files:delete` | Soft delete; `?hard_delete=true` removes bytes → 200 |
| GET | `/files/{file_id}/versions` | `files:read` | Every version, newest first → 200 |
| POST | `/files/{file_id}/versions` | `files:write` | Upload a new version → 201 |

### Spreadsheets

Edits never change stored bytes; each one creates a new version.

| Method | Path | Permission | Purpose → success |
| --- | --- | --- | --- |
| POST | `/files/spreadsheet/create?filename=` | `files:write` | `{data: {sheet: rows}, format, headers?}`, format `xlsx`, `ods` or `csv` → 201 file |
| GET | `/files/{file_id}/spreadsheet/read` | `files:read` | Cell values, `?sheet_name=` → 200 |
| GET | `/files/{file_id}/spreadsheet/info` | `files:read` | Sheet names and sizes → 200 |
| PUT | `/files/{file_id}/spreadsheet/update` | `files:write` | `{data, sheet_name?}` → 200 new version |
| DELETE | `/files/{file_id}/spreadsheet/sheet/{sheet_name}` | `files:delete` | Remove a sheet (not the last) → 200 new version |

Accepted upload types are `file_allowed_types` (images, PDF, text, JSON, XML, YAML, zip, xlsx,
ods); HTML, XHTML and SVG are always refused. Limits: `file_max_size` (100 MB),
`file_user_quota_bytes` (5 GiB), `file_max_versions` (100), `file_spreadsheet_max_cells`
(1,000,000). Text cells starting with `=` or `@`, or with `+`/`-` when not a number, are stored with a leading apostrophe
so they never run as formulas.
