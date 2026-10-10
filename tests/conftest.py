"""In-memory stand-ins for Mongo and Redis so the data layer runs without servers."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.cache.memory import MemoryCache
from app.models.user import UserCreate  # noqa: F401 - re-exported for tests
from app.services.cache import CacheService
from app.services.data.data_service import DataService
from app.services.database_service import DatabaseService
from config import Config


class FakeDatabase:
    """Mirrors the MongoDB backend's contract: ``$set`` updates, matched-count results."""

    client = object()

    def __init__(self) -> None:
        self.collections: dict[str, list[dict[str, Any]]] = {}

    @classmethod
    def _matches(cls, doc: dict[str, Any], filters: dict[str, Any]) -> bool:
        """The subset of MongoDB query syntax the application uses."""
        for key, expected in filters.items():
            if key == "$and":
                ok = all(cls._matches(doc, f) for f in expected)
            elif key == "$or":
                ok = any(cls._matches(doc, f) for f in expected)
            elif isinstance(expected, dict) and any(k.startswith("$") for k in expected):
                value = doc.get(key)
                ok = all(
                    {
                        "$lt": lambda v, e: v is not None and v < e,
                        "$lte": lambda v, e: v is not None and v <= e,
                        "$exists": lambda v, e: (v is not None) == e,
                        "$gt": lambda v, e: v is not None and v > e,
                        "$in": lambda v, e: (
                            v in e or (isinstance(v, list) and bool(set(v) & set(e)))
                        ),
                    }[op](value, operand)
                    for op, operand in expected.items()
                )
            else:
                ok = doc.get(key) == expected
            if not ok:
                return False
        return True

    def _matching(self, collection: str, filters: dict[str, Any]) -> list[dict]:
        return [d for d in self.collections.get(collection, []) if self._matches(d, filters)]

    async def get_record(self, collection, filters):
        found = self._matching(collection, filters)
        return dict(found[0]) if found else None

    async def find_many(self, collection, filters, *, limit=None, skip=0, sort=None):
        docs = [dict(doc) for doc in self._matching(collection, filters)]
        for field, direction in reversed(sort or []):
            docs.sort(key=lambda d: d.get(field), reverse=direction < 0)
        return docs[skip : skip + limit] if limit else docs[skip:]

    async def count(self, collection, filters):
        return len(self._matching(collection, filters))

    async def insert_record(self, collection, data):
        self.collections.setdefault(collection, []).append(dict(data))
        return True

    async def update_record(self, collection, filters, data):
        found = self._matching(collection, filters)
        if found:
            found[0].update(data)
        return bool(found)

    async def update_many(self, collection, filters, data):
        found = self._matching(collection, filters)
        for doc in found:
            doc.update(data)
        return len(found)

    async def upsert_record(self, collection, filters, data):
        if not await self.update_record(collection, filters, data):
            await self.insert_record(collection, {**filters, **data})
        return True

    async def delete_record(self, collection, filters):
        found = self._matching(collection, filters)
        if found:
            self.collections[collection].remove(found[0])
        return bool(found)

    async def increment_field(self, collection, filters, field, amount=1):
        found = self._matching(collection, filters)
        if not found:
            return None
        found[0][field] = (found[0].get(field) or 0) + amount
        return found[0][field]

    async def ensure_indexes(self, indexes):
        self.indexes = indexes

    async def drop_indexes(self, indexes):
        self.dropped = [*getattr(self, "dropped", []), indexes]

    async def health_check(self):
        return True

    async def connect(self):
        return None

    async def close(self):
        return None


@pytest.fixture
def config(tmp_path) -> Config:
    cfg = Config(config_dir=tmp_path)
    cfg.data.update(
        {
            "app_database_provider": "mongodb",
            "app_cache_provider": "memory",
            "cache_prefix": "cache:",
        }
    )
    return cfg


@pytest.fixture
def data_service(config):
    logger = MagicMock()
    database_service = DatabaseService(config, logger)
    database_service.backend = FakeDatabase()
    cache_service = CacheService(config, logger)
    cache_service.backend = MemoryCache(config, logger)
    asyncio.run(cache_service.backend.connect())
    return DataService(
        config, logger, database_service=database_service, cache_service=cache_service
    )


def run(coro):
    return asyncio.run(coro)


def build_test_app(tmp_path, **overrides):
    """The real application with in-memory stand-ins for Mongo; returns (app, services)."""
    from app.api.app import create_app

    config = Config()
    settings = {
        "app_cache_provider": "memory",
        "log_to_file": False,
        "cookie_secure": False,  # the test client speaks plain HTTP
        "file_storage_base_path": str(tmp_path / "uploads"),
        "rate_limit_enabled": False,
        "jwt_secret": "test-secret-" + "x" * 32,
        **overrides,
    }
    config.data.update(settings)
    app = create_app(config)
    services = app.state.services
    services.database_service.backend = FakeDatabase()
    run(services.cache_service.connect())
    return app, services


@pytest.fixture
def env(monkeypatch, tmp_path):
    app, services = build_test_app(tmp_path)
    services.auth_service.refresh_reuse_grace_seconds = 0

    sent_tokens: list[str] = []

    async def capture_email(config, logger, to, token):
        sent_tokens.append(token)
        return True

    monkeypatch.setattr("app.services.auth.service.send_password_reset_email", capture_email)

    class Env:
        pass

    Env.app = app
    Env.services = services
    Env.auth_service = services.auth_service
    Env.file_service = services.file_service
    Env.reset_tokens = sent_tokens
    Env.client = staticmethod(lambda: TestClient(app))
    return Env
