# Extending the boilerplate

A new resource ("part", "order", ...) touches five small places. Follow an existing one
(`files` is the fullest example).

1. **Model** `app/models/part.py`: pydantic `BaseModel`s for request and response bodies.
2. **Data** `app/services/data/parts_ops.py`: a class holding the collection name and the
   queries (`create`, `get`, `list` with `limit/skip/sort`, `update`...). Use `DataService.update`
   for edits (`set` is an upsert) and the `CachePolicy` that fits (`DB_ONLY` for anything
   security-relevant). Register it in `DataService.__init__` (`self.parts = PartsOps(self)`) and
   declare its indexes in `services/data/schema.py`.
3. **Rules** `app/services/part_service.py` if there is logic beyond CRUD; build it in
   `services/registry.py::build_services` and add the field to `Services`.
4. **Routes** `app/api/routes/parts.py`: a router using `Depends(get_current_user)` and a
   dependency from `app/api/deps.py` (add `get_part_service` there); include it in
   `AppFactory.__setup_routes`. Return `HTTPException` for client errors: handlers turn them
   into `application/problem+json`.
5. **Permissions**: the RBAC middleware requires `parts:read|write|delete` (resource = first URL
   segment, action from the method). Grant them to roles in `config.toml`. The test
   `test_every_authenticated_api_route_is_grantable_to_a_normal_user` fails until a role holds
   every permission your routes demand, so you cannot forget this step.

Then add a test that goes through the real app (copy `tests/test_features.py`: `env.client()`,
register, sign in, call your endpoints).

## Other common changes

* **A new setting**: add a field to `Settings` in `app/settings.py` (type, default,
  description), read it as `config["name"]`, run `make config-docs`. A test fails if
  `docs/CONFIGURATION.md` is stale.
* **A data migration**: append a `Migration(n, "what", fn)` to `services/data/migrations.py`;
  it runs once at startup and is recorded in `schema_migrations`. Never edit released ones.
* **A different cache / database / storage**: implement `CacheInterface` /
  `DatabaseInterface` / `StorageInterface` and set `app_cache_provider` /
  `app_database_provider` / `file_storage_backend` to `package.module:ClassName`.
  A storage backend only has to implement the abstract methods; override `save_stream` /
  `open_stream` to avoid buffering whole files, and `download_url` to offer direct downloads.
* **A public endpoint**: add its path to `public_paths`. **An admin-only one**: `admin_only_paths`.
* **Making a retried POST safe**: clients send `Idempotency-Key`; nothing else to do.
* **A stricter rate limit for some paths**: `rate_limit_tiers` in `config.toml`.
