# AGENTS.md

Instructions for AI coding agents (Claude Code, Codex, Copilot, Cursor, Gemini, ...) working in
this repository. People: [CONTRIBUTING.md](CONTRIBUTING.md) says the same at more length.

## Rule zero: the standards are a gate

Every change must meet [docs/STANDARDS.md](docs/STANDARDS.md). A pull request that does not is
closed, whether a person or an agent wrote it. Section 12 there adds the rules specific to
AI-written contributions: state that the change is AI-assisted and paste the real output of
`make lint` and `make test`.

## Navigate with the code graph, not by reading everything

`graphify-out/` holds a knowledge graph of the whole repository (2,000+ nodes: modules, classes,
functions, docs, and the edges between them). A workflow rebuilds it on every push to
`develop`, and `make hooks` installs a post-commit hook that rebuilds it locally. Use it before
opening files:

1. **Read `graphify-out/GRAPH_REPORT.md` first:** god nodes (the core abstractions), communities
   (the modules and what belongs together), surprising cross-links and import cycles.
2. **Ask the graph** instead of grepping or reading whole directories:
   ```bash
   graphify query "how does a request get authorized"   # relevant subgraph, token-capped
   graphify explain "RBACService"                         # a node and its neighbours
   graphify path "FileService" "S3Storage" --undirected  # how two things connect
   graphify affected "CacheService"                       # what a change would impact
   graphify god-nodes                                     # the architectural hubs
   ```
3. **Then read only the files the graph points to**, in full, before editing them.
4. **Check freshness.** The report says `Built from commit: <sha>`. If files you depend on changed
   after that commit, run `make graph` (AST only, about two seconds, no API key).

Install the CLI with `pipx install graphifyy==0.9.80` (or `uv tool install graphifyy==0.9.80`).

## What this is

A production-ready, API-only FastAPI service. Storage-agnostic: MongoDB, Redis, local disk and S3
ship as implementations of `DatabaseInterface`, `CacheInterface` and `StorageInterface`; no
driver is imported outside its backend module. Python 3.11. Overview:
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Commands

```bash
make setup        # create .venv, install, write .env and config.local.toml
make test         # pytest, 197 tests, no services needed (~10 s)
make lint         # ruff check + format check (CI runs this)
make fmt          # ruff fix + format
make config-docs  # regenerate docs/CONFIGURATION.md after changing app/settings.py
make openapi      # regenerate docs/reference/openapi.json after changing any route or model
make graph        # rebuild graphify-out/
make hooks        # pre-commit (ruff) + graphify post-commit hook
make up / make run  # Docker MongoDB + Redis, then the API
```

Finish every change with `make fmt && make lint && make test`.

## Where things go

| Change | Place |
| --- | --- |
| New resource | model `app/models/`, ops `app/services/data/*_ops.py` (+ register in `DataService`, indexes in `schema.py`), routes `app/api/routes/`, include in `AppFactory.__setup_routes`, permissions in `config.toml`. Guide: docs/how-to/add-a-resource.md |
| Business rule | a service in `app/services/`, built in `services/registry.py::build_services` |
| Setting | a field with type, default, description in `app/settings.py`; read as `config["name"]` |
| Data migration | append to `app/services/data/migrations.py`; never edit a released one |
| New database, cache or storage | implement the interface; contract in docs/how-to/write-a-backend.md |

## Rules that are checked in review

- Routes contain no business logic; services never import a driver (`motor`, `pymongo`,
  `redis`, `boto3`); queries use only the documented filter vocabulary.
- `DataService.update` for edits (`set` is an upsert). Security decisions read with
  `CachePolicy.DB_ONLY` / `fresh=True`, never the cache.
- Client errors raise `HTTPException` (they become problem+json); never leak internals.
- Collection endpoints are paged; every route's `<resource>:<action>` is granted in `config.toml`.
- New logic has tests through the real app (`env` fixture), including failure branches; bug
  fixes have a regression test.
- Docs, `CHANGELOG.md` (*Unreleased*) and the code graph change in the same pull request.
- No secrets in code, tests or logs. Environment variables use the `FABP_` prefix.
- No new dependency without agreement in an issue; pin it in `requirements*.txt`.
- Do not invent APIs, settings or files; if the graph does not have it, it does not exist yet.
- Stay in scope: unrelated refactors go in a separate pull request.
