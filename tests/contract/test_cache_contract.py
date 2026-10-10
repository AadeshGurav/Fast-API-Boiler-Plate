"""What every ``CacheInterface`` backend must do."""

from __future__ import annotations

import asyncio

import pytest


async def test_set_then_get_round_trips_json_values(cache):
    backend, prefix = cache
    value = {"a": 1, "b": [1, 2, {"c": "d"}], "e": None}
    assert await backend.set(f"{prefix}k", value) is True
    assert await backend.get(f"{prefix}k") == value


async def test_missing_key_is_none(cache):
    backend, prefix = cache
    assert await backend.get(f"{prefix}missing") is None


async def test_value_expires_after_its_ttl(cache):
    backend, prefix = cache
    await backend.set(f"{prefix}k", "v", ttl=1)
    await asyncio.sleep(1.5)
    assert await backend.get(f"{prefix}k") is None


async def test_add_stores_only_when_absent(cache):
    backend, prefix = cache
    assert await backend.add(f"{prefix}k", "first") is True
    assert await backend.add(f"{prefix}k", "second") is False
    assert await backend.get(f"{prefix}k") == "first"


async def test_concurrent_adds_have_exactly_one_winner(cache):
    backend, prefix = cache
    wins = await asyncio.gather(*(backend.add(f"{prefix}k", n) for n in range(20)))
    assert wins.count(True) == 1


async def test_delete_counts_existing_keys_only(cache):
    backend, prefix = cache
    await backend.set(f"{prefix}a", 1)
    await backend.set(f"{prefix}b", 2)
    assert await backend.delete(f"{prefix}a", f"{prefix}b", f"{prefix}ghost") == 2
    assert await backend.get(f"{prefix}a") is None


async def test_delete_prefix_removes_only_that_prefix(cache):
    backend, prefix = cache
    await backend.set(f"{prefix}x:1", 1)
    await backend.set(f"{prefix}x:2", 2)
    await backend.set(f"{prefix}y:1", 3)
    assert await backend.delete_prefix(f"{prefix}x:") == 2
    assert await backend.get(f"{prefix}y:1") == 3


async def test_rate_limit_allows_up_to_the_limit_then_reports_retry_after(cache):
    backend, prefix = cache
    decisions = [await backend.hit(f"{prefix}rl", limit=3, window=30) for _ in range(4)]
    assert [d.allowed for d in decisions] == [True, True, True, False]
    assert decisions[-1].retry_after is not None and decisions[-1].retry_after > 0


@pytest.mark.parametrize("sliding", [True, False])
async def test_concurrent_hits_never_exceed_the_limit(cache, sliding):
    backend, prefix = cache
    decisions = await asyncio.gather(
        *(backend.hit(f"{prefix}rl", limit=5, window=30, sliding=sliding) for _ in range(20))
    )
    assert sum(d.allowed for d in decisions) == 5


async def test_health_check_is_true_when_connected(cache):
    backend, _ = cache
    assert await backend.health_check() is True
