"""Translate the application's filter vocabulary into PostgreSQL over JSONB documents.

Each collection is a table ``(pk bigserial, doc jsonb)``. Documents keep their shape; datetimes
are stored as fixed-width UTC ISO strings (``2026-10-11T09:30:00.000000+00:00``), so string
comparison orders them correctly and reads can turn them back into ``datetime`` values.

The vocabulary is the one in docs/how-to/write-a-backend.md: equality (``None`` matches null
or missing; on a list it means "contains"), ``$in``, ``$lt``/``$lte``/``$gt``, ``$exists``,
``$and``/``$or``. Values are always bound parameters, never interpolated.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")
ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+00:00$")
COMPARISONS = {"$lt": "<", "$lte": "<=", "$gt": ">"}


def identifier(name: str) -> str:
    """A safely quoted SQL identifier; refuses anything that is not a plain name."""
    if not IDENTIFIER.match(name):
        raise ValueError(f"Not a valid collection or field name: {name!r}")
    return f'"{name}"'


# ---- values ------------------------------------------------------------------------------
def _encode_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _default(value: Any) -> Any:
    if isinstance(value, datetime):
        return _encode_datetime(value)
    if isinstance(value, set | frozenset | tuple):
        return list(value)
    return str(value)


def _prepare(value: Any) -> Any:
    """Datetimes anywhere in a value become ISO strings; json.dumps only calls ``default``
    for types it cannot encode, and datetime is one of them, but nested ones need a walk."""
    if isinstance(value, datetime):
        return _encode_datetime(value)
    if isinstance(value, dict):
        return {k: _prepare(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_prepare(v) for v in value]
    return value


def dumps(value: Any) -> str:
    return json.dumps(_prepare(value), default=_default)


def decode(value: Any) -> Any:
    """Turn stored ISO UTC strings back into datetimes, recursively."""
    if isinstance(value, str) and ISO_UTC.match(value):
        return datetime.fromisoformat(value)
    if isinstance(value, dict):
        return {k: decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [decode(v) for v in value]
    return value


# ---- filters -----------------------------------------------------------------------------
class Query:
    """Collects bound parameters while a filter is compiled."""

    def __init__(self, first_param: int = 1) -> None:
        self.params: list[Any] = []
        self._next = first_param

    def bind(self, value: Any) -> str:
        self.params.append(value)
        placeholder = f"${self._next}"
        self._next += 1
        return placeholder

    def jsonb(self, value: Any) -> str:
        return f"{self.bind(dumps(value))}::jsonb"


def field(name: str) -> str:
    """The JSONB value at ``name``; dotted names reach into nested objects."""
    parts = name.split(".")
    for part in parts:
        identifier(part)  # validation only
    if len(parts) == 1:
        return f"doc->'{name}'"
    return "doc#>'{" + ",".join(parts) + "}'"


def _equals(query: Query, name: str, value: Any) -> str:
    target = field(name)
    if value is None:
        return f"({target} IS NULL OR {target} = 'null'::jsonb)"
    operand = query.jsonb(value)
    # A scalar on the right of @> matches an array element: "list contains value".
    return f"({target} = {operand} OR (jsonb_typeof({target}) = 'array' AND {target} @> {operand}))"


def _compare(query: Query, name: str, op: str, value: Any) -> str:
    target = field(name)
    sql_op = COMPARISONS[op]
    if isinstance(value, bool) or not isinstance(value, int | float | datetime | str):
        raise ValueError(f"{op} needs a number, string or datetime, got {type(value).__name__}")
    if isinstance(value, int | float):
        return (
            f"(jsonb_typeof({target}) = 'number' AND ({target})::numeric {sql_op} "
            f"{query.bind(value)}::numeric)"
        )
    text = _encode_datetime(value) if isinstance(value, datetime) else value
    # COLLATE "C": byte order, so ISO timestamps and identifiers compare predictably.
    return (
        f"(jsonb_typeof({target}) = 'string' AND ({target} #>> '{{}}') COLLATE \"C\" {sql_op} "
        f'{query.bind(text)} COLLATE "C")'
    )


def _operators(query: Query, name: str, spec: dict[str, Any]) -> str:
    clauses = []
    for op, operand in spec.items():
        if op in COMPARISONS:
            clauses.append(_compare(query, name, op, operand))
        elif op == "$in":
            options = [_equals(query, name, value) for value in operand]
            clauses.append("(" + " OR ".join(options) + ")" if options else "FALSE")
        elif op == "$exists":
            path = name.split(".")
            exists = f"doc ? '{name}'" if len(path) == 1 else f"({field(name)} IS NOT NULL)"
            clauses.append(exists if operand else f"NOT ({exists})")
        else:
            raise ValueError(f"Unsupported filter operator {op!r}")
    return " AND ".join(clauses)


def where(query: Query, filters: dict[str, Any]) -> str:
    """A SQL boolean expression for ``filters`` (``TRUE`` when empty)."""
    clauses = []
    for key, value in filters.items():
        if key in ("$and", "$or"):
            parts = [where(query, part) for part in value]
            joiner = " AND " if key == "$and" else " OR "
            clauses.append("(" + joiner.join(parts) + ")" if parts else "TRUE")
        elif isinstance(value, dict) and value and all(k.startswith("$") for k in value):
            clauses.append(_operators(query, key, value))
        else:
            clauses.append(_equals(query, key, value))
    return " AND ".join(clauses) if clauses else "TRUE"


def order_by(sort: list[tuple[str, int]] | None) -> str:
    """Missing values sort first ascending and last descending, as in MongoDB."""
    if not sort:
        return "pk"
    terms = [
        f"{field(name)} {'ASC NULLS FIRST' if direction > 0 else 'DESC NULLS LAST'}"
        for name, direction in sort
    ]
    return ", ".join([*terms, "pk"])
