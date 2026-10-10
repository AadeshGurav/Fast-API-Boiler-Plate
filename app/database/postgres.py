"""PostgreSQL backend: one JSONB document table per collection (asyncpg).

Select it with ``app_database_provider = "postgres"`` and install ``requirements-postgres.txt``.
Every collection is a table ``(pk bigserial primary key, doc jsonb)`` in the schema named by
``app_database``, so the application's documents and queries work unchanged, and SQL tools can
still read them. Declared indexes become expression indexes; unique ones use ``NULLS NOT
DISTINCT`` (PostgreSQL 15+) so a missing field counts once, as in MongoDB. Time-to-live indexes
are honoured by a purge that runs every ``postgres_ttl_purge_seconds``. ADR 0006 explains the
design and the alternatives.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import asyncpg

from app.core.interfaces.database_interface import DatabaseInterface, DuplicateRecordError
from app.database.postgres_sql import (
    IDENTIFIER,
    Query,
    decode,
    dumps,
    field,
    identifier,
    order_by,
    where,
)

MAX_UNPAGED_RESULTS = 10_000  # same safety net as the MongoDB backend


class PostgresDatabase(DatabaseInterface):
    """PostgreSQL backend (settings: ``postgres_*``; ``app_database`` names the schema)."""

    def __init__(self, config, logger) -> None:
        super().__init__(config, logger)
        self.schema = identifier(config["app_database"])
        self._tables: set[str] = set()
        self._ttl: dict[str, list[tuple[str, int]]] = {}
        self._purger: asyncio.Task | None = None
        self._create_lock = asyncio.Lock()

    # ---- lifecycle -----------------------------------------------------------------------
    async def connect(self) -> None:
        cfg = self.config
        self.client = await asyncpg.create_pool(
            host=cfg["postgres_host"],
            port=cfg["postgres_port"],
            user=cfg["postgres_username"],
            password=cfg["postgres_password"] or None,
            database=cfg["postgres_database"],
            min_size=cfg["postgres_min_pool_size"],
            max_size=cfg["postgres_pool_size"],
            timeout=cfg["postgres_timeout_seconds"],
            command_timeout=cfg["postgres_timeout_seconds"],
            server_settings={"application_name": cfg["app_title"]},
        )
        await self.initialize_db()
        if cfg["postgres_ttl_purge_seconds"]:
            self._purger = asyncio.create_task(self._purge_forever())
        self.logger.info(
            f"Connected to PostgreSQL at {cfg['postgres_host']}:{cfg['postgres_port']}"
        )

    async def initialize_db(self) -> None:
        await self.client.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema}")

    async def close(self) -> None:
        if self._purger is not None:
            self._purger.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._purger
        if self.client is not None:
            await self.client.close()
            self.client = None

    async def drop_database(self) -> None:
        """Remove the schema and everything in it (used by the contract tests)."""
        await self.client.execute(f"DROP SCHEMA IF EXISTS {self.schema} CASCADE")
        self._tables.clear()

    async def health_check(self) -> bool:
        try:
            return await self.client.fetchval("SELECT 1") == 1
        except Exception as e:
            self.logger.error(f"PostgreSQL health check failed: {e}")
            return False

    # ---- tables and indexes ----------------------------------------------------------------
    async def _table(self, collection: str) -> str:
        table = f"{self.schema}.{identifier(collection)}"
        if collection in self._tables:
            return table
        async with self._create_lock:
            if collection not in self._tables:
                try:
                    await self.client.execute(
                        f"CREATE TABLE IF NOT EXISTS {table} "
                        "(pk bigserial PRIMARY KEY, doc jsonb NOT NULL)"
                    )
                except (asyncpg.UniqueViolationError, asyncpg.DuplicateTableError):
                    pass  # another process created it between our check and our create
                self._tables.add(collection)
        return table

    async def ensure_indexes(self, indexes: dict[str, list[dict[str, Any]]]) -> None:
        for collection, specs in indexes.items():
            table = await self._table(collection)
            for spec in specs:
                fields = [name for name, _ in spec["keys"]]
                if "expireAfterSeconds" in spec:
                    self._ttl.setdefault(collection, [])
                    entry = (fields[0], int(spec["expireAfterSeconds"]))
                    self._ttl[collection] = [e for e in self._ttl[collection] if e[0] != fields[0]]
                    self._ttl[collection].append(entry)
                name = identifier(f"{collection}_{'_'.join(fields)}".replace(".", "_")[:55] + "_ix")
                columns = ", ".join(f"({field(f)})" for f in fields)
                if spec.get("unique"):
                    sparse = " AND ".join(f"{field(f)} IS NOT NULL" for f in fields)
                    clause = f" WHERE {sparse}" if spec.get("sparse") else ""
                    nulls = "" if spec.get("sparse") else " NULLS NOT DISTINCT"
                    sql = f"CREATE UNIQUE INDEX IF NOT EXISTS {name} ON {table} ({columns}){nulls}{clause}"
                else:
                    sql = f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({columns})"
                await self.client.execute(sql)

    async def drop_indexes(self, indexes: dict[str, list[str]]) -> None:
        """Drop named indexes. Migrations name MongoDB's indexes (``created_at_-1``); those
        never exist here, so names that are not SQL identifiers are skipped."""
        for names in indexes.values():
            for name in names:
                if IDENTIFIER.match(name):
                    await self.client.execute(
                        f"DROP INDEX IF EXISTS {self.schema}.{identifier(name)}"
                    )

    async def purge_expired(self) -> int:
        """Delete records past their time-to-live; returns how many."""
        removed = 0
        for collection, entries in self._ttl.items():
            table = await self._table(collection)
            for name, seconds in entries:
                query = Query()
                cutoff = datetime.now(UTC) - timedelta(seconds=seconds)
                condition = where(query, {name: {"$lt": cutoff}})
                status = await self.client.execute(
                    f"DELETE FROM {table} WHERE {condition}", *query.params
                )
                removed += int(status.split()[-1])
        return removed

    async def _purge_forever(self) -> None:
        while True:
            await asyncio.sleep(self.config["postgres_ttl_purge_seconds"])
            try:
                removed = await self.purge_expired()
                if removed:
                    self.logger.info(f"Purged {removed} expired record(s)")
            except Exception as e:
                self.logger.error(f"Expired-record purge failed: {e}")

    # ---- reads ---------------------------------------------------------------------------
    @staticmethod
    def _record(row: Any) -> dict[str, Any] | None:
        return None if row is None else decode(json.loads(row["doc"]))

    async def get_record(self, collection: str, filters: dict[str, Any]) -> dict | None:
        table, query = await self._table(collection), Query()
        row = await self.client.fetchrow(
            f"SELECT doc FROM {table} WHERE {where(query, filters)} ORDER BY pk LIMIT 1",
            *query.params,
        )
        return self._record(row)

    async def find_many(
        self,
        collection: str,
        filters: dict[str, Any],
        *,
        limit: int | None = None,
        skip: int = 0,
        sort: list[tuple[str, int]] | None = None,
    ) -> list[dict]:
        table, query = await self._table(collection), Query()
        condition = where(query, filters)
        limit_param = query.bind(limit or MAX_UNPAGED_RESULTS)
        skip_param = query.bind(skip)
        rows = await self.client.fetch(
            f"SELECT doc FROM {table} WHERE {condition} ORDER BY {order_by(sort)} "
            f"LIMIT {limit_param} OFFSET {skip_param}",
            *query.params,
        )
        return [self._record(row) for row in rows]

    async def count(self, collection: str, filters: dict[str, Any]) -> int:
        table, query = await self._table(collection), Query()
        return await self.client.fetchval(
            f"SELECT count(*) FROM {table} WHERE {where(query, filters)}", *query.params
        )

    # ---- writes --------------------------------------------------------------------------
    async def _write(self, sql: str, *params: Any) -> str:
        try:
            return await self.client.execute(sql, *params)
        except asyncpg.UniqueViolationError as e:
            raise DuplicateRecordError(str(e).split("\n")[0]) from e

    async def insert_record(self, collection: str, data: dict[str, Any]) -> bool:
        table = await self._table(collection)
        await self._write(f"INSERT INTO {table} (doc) VALUES ($1::jsonb)", dumps(data))
        return True

    def _first_match(self, table: str, query: Query, filters: dict[str, Any]) -> str:
        # FOR UPDATE re-checks the filter after waiting on a concurrent writer, so of several
        # conditional updates racing on one record exactly one still matches.
        return f"pk = (SELECT pk FROM {table} WHERE {where(query, filters)} ORDER BY pk LIMIT 1 FOR UPDATE)"

    async def update_record(
        self, collection: str, filters: dict[str, Any], data: dict[str, Any]
    ) -> bool:
        table, query = await self._table(collection), Query()
        patch = query.jsonb(data)
        status = await self._write(
            f"UPDATE {table} SET doc = doc || {patch} WHERE {self._first_match(table, query, filters)}",
            *query.params,
        )
        return status.endswith(" 1")

    async def update_many(
        self, collection: str, filters: dict[str, Any], data: dict[str, Any]
    ) -> int:
        table, query = await self._table(collection), Query()
        patch = query.jsonb(data)
        status = await self._write(
            f"UPDATE {table} SET doc = doc || {patch} WHERE {where(query, filters)}", *query.params
        )
        return int(status.split()[-1])

    async def upsert_record(
        self, collection: str, filters: dict[str, Any], data: dict[str, Any]
    ) -> bool:
        if not await self.update_record(collection, filters, data):
            await self.insert_record(collection, {**filters, **data})
        return True

    async def delete_record(self, collection: str, filters: dict[str, Any]) -> bool:
        table, query = await self._table(collection), Query()
        status = await self.client.execute(
            f"DELETE FROM {table} WHERE {self._first_match(table, query, filters)}", *query.params
        )
        return status.endswith(" 1")

    async def increment_field(
        self, collection: str, filters: dict[str, Any], field_name: str, amount: int = 1
    ) -> int | None:
        table, query = await self._table(collection), Query()
        path = query.bind([field_name])
        current = f"COALESCE(({field(field_name)})::numeric, 0)"
        delta = query.bind(amount)
        value = await self.client.fetchval(
            f"UPDATE {table} SET doc = jsonb_set(doc, {path}::text[], to_jsonb({current} + {delta}::numeric)) "
            f"WHERE {self._first_match(table, query, filters)} RETURNING {field(field_name)}",
            *query.params,
        )
        if value is None:
            return None
        number = json.loads(value)
        return int(number) if float(number).is_integer() else number
