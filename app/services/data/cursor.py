"""Cursor (keyset) pagination for collections that grow without bound.

Offset paging makes the database skip every earlier row, and a record inserted while a client
pages shifts every later page. A cursor instead names the last record seen, by its sort value
and a unique tie-breaker, and the next page asks for records strictly after it, which an index
answers directly however deep the client goes.

Cursors are opaque to clients: base64url JSON of ``[sort value, tie-breaker]``. Only
newest-first order is needed today.
"""

from __future__ import annotations

import base64
import binascii
import json
from datetime import datetime
from typing import Any


class InvalidCursorError(ValueError):
    """The cursor was not issued by this API (or was altered)."""


def encode(record: dict[str, Any], sort_field: str, tie_field: str) -> str:
    value = record[sort_field]
    raw = [value.isoformat() if isinstance(value, datetime) else value, record[tie_field]]
    return base64.urlsafe_b64encode(json.dumps(raw).encode()).decode().rstrip("=")


def decode(cursor: str) -> tuple[datetime, str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value, tie = json.loads(base64.urlsafe_b64decode(padded.encode()))
        return datetime.fromisoformat(value), str(tie)
    except (binascii.Error, ValueError, TypeError, json.JSONDecodeError) as e:
        raise InvalidCursorError("Invalid cursor") from e


def after(cursor: str, sort_field: str, tie_field: str) -> dict[str, Any]:
    """The filter for records after ``cursor`` in newest-first order."""
    value, tie = decode(cursor)
    return {
        "$or": [
            {sort_field: {"$lt": value}},
            {sort_field: value, tie_field: {"$lt": tie}},
        ]
    }


def newest_first(sort_field: str, tie_field: str) -> list[tuple[str, int]]:
    return [(sort_field, -1), (tie_field, -1)]
