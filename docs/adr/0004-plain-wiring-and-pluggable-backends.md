# 0004: Plain service wiring and pluggable backends

**Status:** accepted (2026-10-08)

**Context.** A DI framework, an application built at import time and fourteen modules
importing a global container made wiring invisible, tests share state, and (for metrics)
re-created services re-registered the same Prometheus series, crashing the second request.
Redis was modelled as a "database", and five service interfaces had one implementation each.

**Decision.** `build_services()` constructs services explicitly; `create_app()` is a factory;
routes use `app.state.services` through FastAPI dependencies. Interfaces exist only where a
second implementation is plausible (cache, database, storage) and those are loadable by
`package.module:Class`. RBAC definitions are configuration, assignments live on users.

**Alternatives considered.** Keep the container (hidden lifetimes, global state); a registry
of strings (no type checking); interfaces for every service (indirection without a user).

**Consequences.** More lines in one wiring function, fewer in the rest; tests can build several
isolated apps; swapping Redis for another cache is one class.
