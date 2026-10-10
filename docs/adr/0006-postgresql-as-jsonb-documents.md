# 0006: PostgreSQL ships as a JSONB document backend

**Status:** accepted (2026-10-11)

**Context.** Every popular FastAPI template runs on PostgreSQL, and many teams will not operate
MongoDB. Our README claimed any database is "one class away", but no second database proved it.
The application talks to `DatabaseInterface`: document records, a seven-operator filter
vocabulary, an atomic increment, unique and time-to-live indexes
([write a backend](../how-to/write-a-backend.md)).

**Decision.** `app/database/postgres.py` (asyncpg) implements the interface unchanged:

* each collection is a table `(pk bigserial primary key, doc jsonb not null)` in a schema named
  by `app_database`, created on first use;
* filters compile to SQL over `doc` (`postgres_sql.py`): equality with list-contains through
  `@>`, `$in` as OR-ed equalities, numeric comparisons on `::numeric`, string and datetime
  comparisons in byte order (`COLLATE "C"`); every value is a bound parameter and every
  identifier is checked against a strict pattern;
* datetimes are stored as fixed-width UTC ISO strings, so they sort correctly and decode back
  to `datetime`;
* "first match" writes lock the chosen row (`... LIMIT 1 FOR UPDATE`), so conditional updates
  have exactly one winner, which the job queue and two-factor replay protection rely on;
* declared indexes become expression indexes; unique ones use `NULLS NOT DISTINCT`
  (PostgreSQL 15+) so a missing field counts once, as in MongoDB; sparse ones are partial;
* time-to-live indexes are honoured by a purge every `postgres_ttl_purge_seconds`.

The backend passes the same contract suite as MongoDB, and an end-to-end test runs the whole
application on it in CI.

**Alternatives considered.** *Relational tables per collection with SQLAlchemy models and
Alembic*: the natural shape for SQL, but it needs a second model layer beside the Pydantic
models and a migration tool, and it would make every resource a two-place change; teams that
want it can write that backend against the same interface. *SQLModel*: the same costs, plus a
model layer that couples API and storage shapes. *A JSONB column next to typed columns*: needs
per-collection DDL, which is exactly what the interface was meant to avoid.

**Consequences.** Queries use expression indexes, which PostgreSQL plans well for the declared
access paths; ad-hoc reporting reads JSONB (views can flatten it). PostgreSQL 15 or newer is
required. Upserts are update-then-insert, so two first-time upserts of the same key can race
like MongoDB's; declare a unique index where that matters. The backend is optional:
`requirements-postgres.txt`, `INSTALL_POSTGRES=true` for the image.
