"""Losing the cache slows the app down; it does not take it down."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.cache import CacheUnavailableError
from app.services.cache import CacheService
from tests.conftest import build_test_app, run
from tests.test_auth_flow import bearer, login, register


class DownBackend:
    """A cache backend whose network is gone."""

    def __init__(self) -> None:
        self.calls = 0
        self.up = False

    async def _op(self, *args, **kwargs):
        self.calls += 1
        if not self.up:
            raise ConnectionError("redis is down")
        return "ok"

    get = set = add = delete = delete_prefix = hit = _op

    async def close(self) -> None:
        pass


@pytest.fixture
def cache(config):
    service = CacheService(config, MagicMock())
    service.backend = DownBackend()
    return service


def test_reads_become_misses_and_writes_are_skipped(cache):
    assert run(cache.get("k")) is None
    assert run(cache.set("k", 1)) is False
    assert run(cache.delete("k")) == 0
    assert run(cache.clear_pattern("k*")) == 0


def test_after_one_failure_the_backend_is_left_alone_until_the_cooldown_ends(cache, monkeypatch):
    run(cache.get("k"))
    assert cache.backend.calls == 1 and cache.available is False

    for _ in range(50):
        run(cache.get("k"))
    assert cache.backend.calls == 1  # no per-request timeouts while the circuit is open

    cache.backend.up = True
    after_cooldown = cache._skip_until + 1
    monkeypatch.setattr("app.services.cache.time.monotonic", lambda: after_cooldown)
    assert run(cache.get("k")) == "ok" and cache.backend.calls == 2


def test_operations_without_a_fallback_say_so(cache):
    with pytest.raises(CacheUnavailableError):
        run(cache.add("claim", {}))
    with pytest.raises(CacheUnavailableError):
        run(cache.hit("ip", 10, 60))


def test_app_still_serves_authenticated_requests_with_the_cache_down(tmp_path):
    from fastapi.testclient import TestClient

    app, services = build_test_app(tmp_path)
    with TestClient(app) as client:
        register(client)
        client.headers.update(bearer(login(client, "ada")))
        services.cache_service.backend = DownBackend()

        assert client.get("/api/v1/auth/me").status_code == 200  # DB answers instead

        keyed = client.post(
            "/api/v1/files/upload",
            files={"file": ("a.txt", b"hello", "text/plain")},
            headers={"Idempotency-Key": "needs-the-cache-1"},
        )
        assert keyed.status_code == 503 and keyed.headers["retry-after"] == "5"

        unkeyed = client.post(
            "/api/v1/files/upload", files={"file": ("a.txt", b"hello", "text/plain")}
        )
        assert unkeyed.status_code == 201
