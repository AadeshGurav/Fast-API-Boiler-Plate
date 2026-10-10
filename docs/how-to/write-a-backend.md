# Bring your own database, cache or storage

The application is storage-agnostic. Routes, services and the data layer talk to three
interfaces, never to a driver: no `motor`, `pymongo`, `redis` or `boto3` import exists outside
its backend module. Swap MongoDB for PostgreSQL, Redis for Memcached, or local disk for Azure
Blob by writing one class and changing one setting. **No application code changes.**

MongoDB, PostgreSQL, Redis, in-memory cache, local disk and S3 ship as complete
implementations; MongoDB and Redis are the defaults, not requirements. Two database backends
with very different engines (`app/database/mongodb.py`, `app/database/postgres.py`) pass the
same contract suite: read either as a reference.

| To replace | Implement | Select it with |
| --- | --- | --- |
| Database (MongoDB) | `DatabaseInterface` (`app/core/interfaces/database_interface.py`) | `app_database_provider = "package.module:YourDatabase"` |
| Cache (Redis, memory) | `CacheInterface` (`app/cache/interface.py`) | `app_cache_provider = "package.module:YourCache"` |
| File storage (local, S3) | `StorageInterface` (`app/core/interfaces/storage_interface.py`) | `file_storage_backend = "package.module:YourStorage"` |

Each class is constructed with `(config, logger)`; read your own settings from `config`
(add them to `app/settings.py`). Built-in names (`mongodb`, `redis`, `memory`, `local`, `s3`)
and dotted paths are resolved by `app/core/plugins.py::load_backend_class`.

## A database backend

### The record model

Records are plain dicts. `id` is the application's identifier (a string); return records with
`id` and without any engine-specific key (the MongoDB backend maps `_id` away). Values can be
nested: `profile` and `metadata` are objects, `roles`, `groups` and `tags` are lists, and
datetimes are timezone-aware UTC. A relational backend stores these as JSON columns or a
document table, or maps the [collections](../reference/data-model.md) to tables.

### The methods

| Method | Contract |
| --- | --- |
| `connect()` / `close()` | Open and release connections; set `self.client` (anything not `None` means connected). |
| `health_check()` | `True` if the backend answers right now. |
| `initialize_db()` | Backend-level setup; may do nothing. |
| `get_record(collection, filters)` | First matching record or `None`. |
| `find_many(collection, filters, *, limit, skip, sort)` | Matching records; `sort` is `[(field, 1 or -1)]`. Without `limit`, cap the result (MongoDB caps at 10,000). |
| `count(collection, filters)` | Number of matches. |
| `insert_record(collection, data)` | Insert; `True` when stored. On a unique-index violation raise `DuplicateRecordError` (`app.core.interfaces.database_interface`), never a driver exception; `update_record`, `update_many` and `upsert_record` do the same. |
| `update_record(collection, filters, data)` | Set `data`'s fields on the first match; `True` if one matched. **Never inserts.** |
| `update_many(collection, filters, data)` | Set fields on every match; return how many matched. |
| `upsert_record(collection, filters, data)` | Update the match, or insert `filters` + `data`. |
| `delete_record(collection, filters)` | Delete the first match; `True` if one was deleted. |
| `increment_field(collection, filters, field, amount)` | **Atomically** add and return the new value (`None` if no match). Lockout correctness depends on it. |
| `ensure_indexes(indexes)` / `drop_indexes(indexes)` | Apply the declared indexes; ignore ones you cannot or need not build. |

### The filter vocabulary

Filters are dicts in a small, fixed vocabulary. This is everything the application uses:

| Form | Meaning |
| --- | --- |
| `{"field": value}` | Equality. `{"field": None}` matches null **or missing**. |
| `{"field": value}` where the stored field is a list | Matches if the list contains `value`. |
| `{"field": {"$in": [a, b]}}` | Equals any of the values; on a list field, shares any element. |
| `{"field": {"$lt" / "$lte" / "$gt": x}}` | Comparison (numbers and datetimes). |
| `{"field": {"$exists": False}}` | Field missing. |
| `{"$and": [f1, f2]}`, `{"$or": [f1, f2]}` | Combine filters. |

Several conditions in one dict are combined with AND. A reference implementation of the whole
vocabulary, about forty lines, is `FakeDatabase._matches` in `tests/conftest.py`; a SQL backend
translates the same forms into `WHERE` clauses.

### Index declarations

`app/services/data/schema.py` declares indexes as
`{"keys": [(field, 1 or -1), ...], **options}`. The options used are:

- `unique`: **must be enforced**: usernames, emails and file versions rely on it.
- `sparse`: a unique index that ignores records without the field (email).
- `expireAfterSeconds`: time-to-live. Sessions, reset tokens and login attempts expire.
  Correctness does not depend on it (expiry is also checked when records are read), so a backend
  may implement it with a scheduled delete instead.

### Prove it

Run the contract suite against your class; it is the definition of "works":

```bash
CONTRACT_DATABASES=package.module:YourClass pytest tests/contract/test_database_contract.py
CONTRACT_CACHES=package.module:YourCache pytest tests/contract/test_cache_contract.py
CONTRACT_DATABASES=package.module:YourClass pytest tests/contract/test_app_on_real_databases.py
```

The last runs the whole application on your backend: migrations, indexes, sign-in, two-factor,
files, the audit log and the job queue. Unique-index violations must raise
`DuplicateRecordError`; give your class a `drop_database()` so test runs clean up after
themselves.

Names are comma-separated (`fake,mongodb`, `memory,redis`, or a dotted path). Connection
settings come from the usual `FABP_*` variables, and each run uses a throwaway database name.
If your class defines `drop_database()` it is called afterwards. Then try the
[tutorial](../tutorials/getting-started.md) against a real server.

## A cache backend

Implement `get`, `set`, `add`, `delete`, `delete_prefix`, `hit`, plus `connect`, `close`,
`health_check` and `is_connected`. Values are JSON-serialisable; `ttl` is seconds.

- `add` stores only if the key is absent and must be **atomic**: idempotency claims and
  chunked-upload sessions rely on it.
- `hit(key, limit, window, sliding=...)` counts one request and returns a `RateDecision`
  (`allowed`, `current`, `retry_after`); it must be **atomic** so concurrent requests cannot
  share the last slot. `app/cache/memory.py` is the readable reference; `app/cache/redis.py`
  does it with Lua scripts.
- Raise on failure; `CacheService` turns failures into graceful degradation for you.

## A storage backend

Implement `save`, `read`, `delete`, `exists`, `get_url`, `list`, `get_size`. Paths are relative
and `/`-separated; **refuse any path that escapes your root**. Then override, when your store
can:

- `save_stream` / `open_stream`: avoid holding whole files in memory (the defaults buffer);
  a failing input stream must leave nothing behind.
- `download_url`: short-lived direct download URLs (enables `file_download_redirect`).
- `purge_older_than`: housekeeping for abandoned chunked uploads.

`app/services/file/storage/local.py` and `s3.py` are complete examples.
