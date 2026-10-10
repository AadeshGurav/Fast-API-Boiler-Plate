"""What every ``DatabaseInterface`` backend must do, whatever it stores data in."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.core.interfaces.database_interface import DuplicateRecordError

COLL = "contract_items"


async def seed(database, *records) -> None:
    for record in records:
        assert await database.insert_record(COLL, dict(record))


async def test_insert_then_get_returns_the_record(database):
    await seed(database, {"id": "a", "name": "alpha", "n": 1})
    found = await database.get_record(COLL, {"id": "a"})
    assert found["id"] == "a" and found["name"] == "alpha" and found["n"] == 1


async def test_get_unknown_record_is_none(database):
    assert await database.get_record(COLL, {"id": "missing"}) is None


async def test_update_changes_only_the_given_fields(database):
    await seed(database, {"id": "a", "name": "alpha", "n": 1})
    assert await database.update_record(COLL, {"id": "a"}, {"n": 2}) is True
    found = await database.get_record(COLL, {"id": "a"})
    assert (found["name"], found["n"]) == ("alpha", 2)


async def test_update_unknown_record_returns_false_and_inserts_nothing(database):
    assert await database.update_record(COLL, {"id": "ghost"}, {"n": 2}) is False
    assert await database.count(COLL, {}) == 0


async def test_update_many_reports_how_many_matched(database):
    await seed(database, {"id": "a", "g": 1}, {"id": "b", "g": 1}, {"id": "c", "g": 2})
    assert await database.update_many(COLL, {"g": 1}, {"flag": True}) == 2
    assert await database.count(COLL, {"flag": True}) == 2
    assert await database.update_many(COLL, {"g": 99}, {"flag": True}) == 0


async def test_upsert_inserts_when_missing_and_updates_when_present(database):
    assert await database.upsert_record(COLL, {"id": "a"}, {"n": 1}) is True
    assert await database.upsert_record(COLL, {"id": "a"}, {"n": 2}) is True
    assert await database.count(COLL, {"id": "a"}) == 1
    assert (await database.get_record(COLL, {"id": "a"}))["n"] == 2


async def test_delete_removes_one_record_and_reports_it(database):
    await seed(database, {"id": "a"}, {"id": "b"})
    assert await database.delete_record(COLL, {"id": "a"}) is True
    assert await database.delete_record(COLL, {"id": "a"}) is False
    assert await database.count(COLL, {}) == 1


async def test_unique_index_rejects_a_duplicate_insert(database):
    await database.ensure_indexes({COLL: [{"keys": [("email", 1)], "unique": True}]})
    await seed(database, {"id": "a", "email": "x@example.com"})
    with pytest.raises(DuplicateRecordError):
        await database.insert_record(COLL, {"id": "b", "email": "x@example.com"})
    assert await database.count(COLL, {}) == 1


async def test_unique_index_rejects_an_update_that_collides(database):
    await database.ensure_indexes({COLL: [{"keys": [("email", 1)], "unique": True}]})
    await seed(
        database, {"id": "a", "email": "a@example.com"}, {"id": "b", "email": "b@example.com"}
    )
    with pytest.raises(DuplicateRecordError):
        await database.update_record(COLL, {"id": "b"}, {"email": "a@example.com"})


async def test_sparse_unique_index_ignores_records_without_the_field(database):
    await database.ensure_indexes(
        {COLL: [{"keys": [("handle", 1)], "unique": True, "sparse": True}]}
    )
    await seed(database, {"id": "a"}, {"id": "b"})
    await seed(database, {"id": "c", "handle": "h"})
    with pytest.raises(DuplicateRecordError):
        await database.insert_record(COLL, {"id": "d", "handle": "h"})


async def test_ensure_indexes_can_run_twice(database):
    spec = {COLL: [{"keys": [("email", 1)], "unique": True}]}
    await database.ensure_indexes(spec)
    await database.ensure_indexes(spec)


async def test_increment_returns_the_new_value_and_creates_the_field(database):
    await seed(database, {"id": "a"}, {"id": "b", "n": 5})
    assert await database.increment_field(COLL, {"id": "a"}, "n") == 1
    assert await database.increment_field(COLL, {"id": "b"}, "n", 3) == 8
    assert await database.increment_field(COLL, {"id": "ghost"}, "n") is None


async def test_concurrent_increments_never_lose_or_repeat_a_value(database):
    await seed(database, {"id": "a", "n": 0})
    results = await asyncio.gather(
        *(database.increment_field(COLL, {"id": "a"}, "n") for _ in range(50))
    )
    assert sorted(results) == list(range(1, 51))
    assert (await database.get_record(COLL, {"id": "a"}))["n"] == 50


@pytest.mark.parametrize(
    ("filters", "expected"),
    [
        ({"n": 2}, {"b"}),
        ({"n": {"$gt": 2}}, {"c", "d"}),
        ({"n": {"$lt": 2}}, {"a"}),
        ({"n": {"$lte": 2}}, {"a", "b"}),
        ({"n": {"$gt": 1, "$lt": 4}}, {"b", "c"}),
        ({"n": {"$in": [1, 4]}}, {"a", "d"}),
        ({"tag": {"$exists": True}}, {"a", "c"}),
        ({"tag": {"$exists": False}}, {"b", "d"}),
        ({"$or": [{"n": 1}, {"n": 4}]}, {"a", "d"}),
        ({"$and": [{"n": {"$gt": 1}}, {"tag": "x"}]}, {"c"}),
        ({"n": {"$gt": 1}, "tag": "x"}, {"c"}),
    ],
)
async def test_filter_vocabulary(database, filters, expected):
    await seed(
        database,
        {"id": "a", "n": 1, "tag": "x"},
        {"id": "b", "n": 2},
        {"id": "c", "n": 3, "tag": "x"},
        {"id": "d", "n": 4},
    )
    found = await database.find_many(COLL, filters)
    assert {record["id"] for record in found} == expected
    assert await database.count(COLL, filters) == len(expected)


async def test_find_many_sorts_pages_and_skips(database):
    await seed(database, *({"id": f"r{n}", "n": n} for n in range(1, 6)))
    ascending = await database.find_many(COLL, {}, sort=[("n", 1)])
    assert [r["n"] for r in ascending] == [1, 2, 3, 4, 5]
    page = await database.find_many(COLL, {}, sort=[("n", -1)], limit=2, skip=1)
    assert [r["n"] for r in page] == [4, 3]


async def test_records_keep_their_own_id(database):
    await seed(database, {"id": "business-id-1", "n": 1})
    found = await database.find_many(COLL, {})
    assert [r["id"] for r in found] == ["business-id-1"]


async def test_health_check_is_true_when_connected(database):
    assert await database.health_check() is True


async def test_datetimes_come_back_timezone_aware_utc(database):
    moment = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    await seed(database, {"id": "a", "at": moment})
    stored = (await database.get_record(COLL, {"id": "a"}))["at"]
    assert stored == moment and stored.utcoffset() == timedelta(0)


async def test_conditional_update_has_exactly_one_winner(database):
    """A job queue claims work with ``update_record({id, status: queued}, {status: running})``."""
    await seed(database, {"id": "job", "status": "queued"})
    claims = await asyncio.gather(
        *(
            database.update_record(COLL, {"id": "job", "status": "queued"}, {"status": "running"})
            for _ in range(20)
        )
    )
    assert claims.count(True) == 1


async def test_compound_unique_index_is_on_the_combination(database):
    await database.ensure_indexes({COLL: [{"keys": [("owner", 1), ("name", 1)], "unique": True}]})
    await seed(database, {"id": "a", "owner": "u1", "name": "x"})
    await seed(
        database, {"id": "b", "owner": "u1", "name": "y"}, {"id": "c", "owner": "u2", "name": "x"}
    )
    with pytest.raises(DuplicateRecordError):
        await database.insert_record(COLL, {"id": "d", "owner": "u1", "name": "x"})


async def test_upsert_into_a_duplicate_raises(database):
    await database.ensure_indexes({COLL: [{"keys": [("email", 1)], "unique": True}]})
    await seed(database, {"id": "a", "email": "a@example.com"})
    with pytest.raises(DuplicateRecordError):
        await database.upsert_record(COLL, {"id": "b"}, {"email": "a@example.com"})


async def test_update_many_into_a_duplicate_raises(database):
    await database.ensure_indexes({COLL: [{"keys": [("email", 1)], "unique": True}]})
    await seed(database, {"id": "a", "g": 1, "email": "a@example.com"}, {"id": "b", "g": 2})
    with pytest.raises(DuplicateRecordError):
        await database.update_many(COLL, {"id": "b"}, {"email": "a@example.com"})


async def test_equality_on_a_list_field_means_contains(database):
    await seed(database, {"id": "a", "tags": ["x", "y"]}, {"id": "b", "tags": ["z"]})
    assert {r["id"] for r in await database.find_many(COLL, {"tags": "x"})} == {"a"}
    found = await database.find_many(COLL, {"tags": {"$in": ["y", "z"]}})
    assert {r["id"] for r in found} == {"a", "b"}


async def test_none_matches_null_or_missing_and_exists_false_means_missing(database):
    await seed(database, {"id": "a", "v": None}, {"id": "b"}, {"id": "c", "v": 1})
    assert {r["id"] for r in await database.find_many(COLL, {"v": None})} == {"a", "b"}
    assert {r["id"] for r in await database.find_many(COLL, {"v": {"$exists": False}})} == {"b"}
