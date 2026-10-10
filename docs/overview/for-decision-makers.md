# For decision makers

**In one sentence:** a ready-made, security-reviewed back end that handles accounts, access
rights and files, so a team can spend its first weeks on the product instead of on plumbing.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../diagrams/system-context-dark.svg">
  <img alt="System context: clients reach one FastAPI service through an optional reverse proxy; the service uses MongoDB, Redis and file storage, and optionally Google sign-in, SMTP and observability tools." src="../diagrams/system-context.svg">
</picture>

## What you get on day one

| Capability | What it means for the product |
| --- | --- |
| Accounts | Sign-up, sign-in, "remember me", sign out of one or all devices, password change and reset by email, optional Google sign-in. |
| Access control | Roles (admin, manager, user, guest), groups, and time-limited grants, all defined in one config file. Every endpoint is locked unless a role allows it. |
| Files | Per-user uploads with version history, large uploads in chunks, image thumbnails, spreadsheet read and edit (xlsx, ods, csv), per-user storage quota. |
| Protection | Rate limits, request size and time limits, overload shedding, safe retries, cross-site request checks, security headers. |
| Operations | Health probes for orchestrators, structured logs, optional metrics, tracing and error reporting. |
| Developer experience | One command to set up, one to run, 197 automated tests that need no database, CI on every push. |

## Why it can be trusted

- **Reviewed and hardened.** A security audit's findings are each pinned by a regression test
  (`tests/test_security_fixes.py`): account-takeover through Google sign-in, brute-force races,
  oversized or malicious files, cross-site requests, leaked secrets in error reports.
- **Decisions are written down.** Five [architecture decision records](../adr/) explain the
  main choices and the alternatives that were rejected.
- **Fails safely.** Wrong configuration stops startup with a message naming the problem.
  Losing the cache slows the service down instead of taking it down
  ([how](../how-to/operate.md#redis-is-down)).

## What it costs to run

One container image plus three backing services; nothing is licensed.

| Piece | Needed | Notes |
| --- | --- | --- |
| The API container | always | Python 3.11. Scale by adding containers once Redis and S3 are in use. |
| MongoDB 8 | always | Holds users, sessions and file records. Plan backups. |
| Redis 7 | recommended | Cache, rate limits, safe retries. A single-process memory cache works for small or test deployments. |
| S3-compatible storage | when more than one server | Local disk is fine for one server. |
| Reverse proxy | for internet traffic | TLS and connection timeouts. Any proxy works. |
| SMTP, Sentry, Prometheus, OpenTelemetry | optional | Off by default. |

[Deploy](../how-to/deploy.md) has the detail.

## What it does not do (yet)

Knowing the edges avoids surprises in planning:

- **No user interface.** It is API-only by design ([ADR 0002](../adr/0002-api-only.md)); screens
  are a separate project. [For designers](../design/for-designers.md) describes what those
  screens need to handle.
- **No product logic.** There are no domain objects yet; adding one is a routine change
  ([add a resource](../how-to/add-a-resource.md)).
- **One organisation.** There is no multi-tenancy: all users share one space, separated only by
  ownership of their own files and by roles.
- **One sign-in provider.** Google only; linking a provider to an already signed-in account
  answers "not implemented".
- **Audit trail covers sign-ins only.** Every login attempt is recorded for 90 days; other
  actions are logged but not stored as an audit history.
- **Known engineering limits** are listed in [Architecture → Known limits](../ARCHITECTURE.md#known-limits).

## Decisions to make before building on it

1. **Tenancy:** will customers share one deployment? If yes, add tenant ownership before the
   first domain object, not after.
2. **File storage:** one server with local disk, or S3 from the start (needed to scale out).
3. **Sign-in:** is Google enough, or are other providers or SSO required?
4. **Audit:** does the product need a stored history of changes (who changed what, when)?

## What changed from the original boilerplate

The earlier version shipped a demo web UI and a home-grown dependency container. Both were
removed, and the API, cache and file storage were rebuilt for safety and scale.
[What changed](what-changed.md) has the full comparison.
