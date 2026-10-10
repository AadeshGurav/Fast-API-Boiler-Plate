"""The PostgreSQL query translator: identifiers are validated, values are always bound."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.database.postgres_sql import Query, decode, dumps, field, identifier, order_by, where

HOSTILE = "x'; DROP TABLE users; --"


@pytest.mark.parametrize("name", [HOSTILE, 'a"b', "a b", "1abc", "", "a" * 64, "a-b"])
def test_identifiers_refuse_anything_but_plain_names(name):
    with pytest.raises(ValueError):
        identifier(name)


def test_hostile_field_names_are_refused_before_any_sql_is_built():
    with pytest.raises(ValueError):
        where(Query(), {HOSTILE: 1})
    with pytest.raises(ValueError):
        order_by([(HOSTILE, 1)])


def test_values_are_bound_never_interpolated():
    query = Query()

    sql = where(query, {"name": HOSTILE, "n": {"$gt": 3}, "tags": {"$in": [HOSTILE]}})

    assert HOSTILE not in sql and "DROP" not in sql
    assert query.params == [f'"{HOSTILE}"', 3, f'"{HOSTILE}"']


def test_every_vocabulary_form_compiles():
    query = Query()
    sql = where(
        query,
        {
            "a": None,
            "b": {"$exists": False},
            "c": {"$lt": 1, "$lte": 2},
            "d": {"$gt": datetime(2026, 1, 1, tzinfo=UTC)},
            "$or": [{"e": 1}, {"f": "x"}],
            "$and": [{"g": True}],
            "profile.city": "Pune",
        },
    )

    assert "NOT (doc ? 'b')" in sql and "doc#>'{profile,city}'" in sql
    assert where(Query(), {}) == "TRUE"
    with pytest.raises(ValueError, match="Unsupported"):
        where(Query(), {"a": {"$regex": ".*"}})


def test_datetimes_round_trip_as_fixed_width_utc():
    ist = timezone(timedelta(hours=5, minutes=30))
    value = {"at": datetime(2026, 10, 11, 9, 30, tzinfo=ist), "nested": [datetime(2026, 1, 1)]}

    stored = dumps(value)
    back = decode(__import__("json").loads(stored))

    assert '"2026-10-11T04:00:00.000000+00:00"' in stored
    assert back["at"] == value["at"] and back["at"].tzinfo is not None
    assert back["nested"][0] == datetime(2026, 1, 1, tzinfo=UTC)
    assert decode("2026-10-11") == "2026-10-11"  # only the exact stored format converts


def test_comparisons_need_a_comparable_operand():
    with pytest.raises(ValueError):
        where(Query(), {"a": {"$lt": True}})
    with pytest.raises(ValueError):
        where(Query(), {"a": {"$gt": ["x"]}})


def test_field_paths():
    assert field("name") == "doc->'name'"
    assert field("a.b") == "doc#>'{a,b}'"
