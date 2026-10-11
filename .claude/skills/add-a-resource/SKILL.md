---
name: add-a-resource
description: Add a new domain resource (orders, parts, projects...) to this FastAPI boilerplate end to end - model, data ops, indexes, optional service, routes, permissions, tests, OpenAPI contract, docs and changelog - following the repository's rules. Use when asked to add an entity, collection, CRUD endpoints or a new API resource.
---

# Add a resource

Follow `docs/how-to/add-a-resource.md`; it has complete code for a `parts` resource. This skill
is the checklist an agent must satisfy, in order. Read `AGENTS.md` and `docs/STANDARDS.md`
first, and ask the code graph before opening files:

```bash
graphify explain "FilesOps"        # the fullest existing resource to imitate
graphify query "how is a collection registered and indexed"
```

## Steps

1. **Model** `app/models/<name>.py`: request and response Pydantic models; validation lives
   here (field limits, `max_length` on every string).
2. **Data ops** `app/services/data/<name>s_ops.py`: one class with the collection name and its
   queries. Use only the filter vocabulary in `docs/how-to/write-a-backend.md` (no driver
   syntax: the app runs on MongoDB and PostgreSQL). `update()` for edits, never `set()`;
   `CachePolicy.DB_ONLY` for anything that decides access. Register it in
   `DataService.__init__`; declare indexes in `app/services/data/schema.py`.
3. **Service** `app/services/<name>_service.py`, only if there is a business rule; build it in
   `services/registry.py::build_services` and add it to `Services`. Security-relevant changes
   call `self.audit.record(...)`.
4. **Routes** `app/api/routes/<name>s.py`: parse, call, shape. No business logic. Ownership
   checks answer 404 for other users' records. Collections are paged (`page`, `page_size`,
   `total`, `has_next`; plus `cursor`/`next_cursor` if unbounded). Include the router in
   `AppFactory.__setup_routes` under `/api/v1`.
5. **Permissions**: grant `<resource>:read|write|delete` to a role in `config.toml`.
6. **Tests** through the real app (`env` fixture, see `tests/test_features.py`), including the
   failure branches: 404 for someone else's record, 422 for invalid input, 403 without the
   permission.
7. **Contract and docs**: `make openapi` (commit the diff); add the endpoints to
   `docs/reference/api.md`, the collection to `docs/reference/data-model.md`, and an entry under
   *Unreleased* in `CHANGELOG.md`.

## Done when

```bash
make fmt && make lint && make test && make fuzz && make graph
```

all pass, and the pull request says it is AI-assisted with the real output of `make lint` and
`make test` (STANDARDS section 12). Never invent settings, APIs or files that the code graph does
not have; add them in the same change or leave them out.
