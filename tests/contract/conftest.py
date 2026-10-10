"""Backend contract fixtures: the same tests run against every database and cache backend.

By default they run against the in-memory stand-ins, so ``make test`` needs no services. Name
real backends to test them too (CI does), reading connection settings from the usual
``FABP_*`` variables:

    CONTRACT_DATABASES=fake,mongodb CONTRACT_CACHES=memory,redis pytest tests/contract

Your own backend is a ``package.module:Class`` entry in the same list.
"""

from __future__ import annotations

import os
import uuid
from unittest.mock import MagicMock

import pytest

from app.cache import BUILTIN_CACHES
from app.core.plugins import load_backend_class
from app.database import BUILTIN_DATABASES
from tests.conftest import FakeDatabase


def _selected(variable: str, default: str) -> list[str]:
    return [name.strip() for name in os.environ.get(variable, default).split(",") if name.strip()]


def _config(tmp_path, **overrides):
    from config import Config

    config = Config(config_dir=tmp_path)
    config.data.update(overrides)
    return config


@pytest.fixture(params=_selected("CONTRACT_DATABASES", "fake"))
async def database(request, tmp_path):
    """A connected, empty database backend; dropped afterwards."""
    if request.param == "fake":
        yield FakeDatabase()
        return
    # A throwaway database name, so a contract run never touches real data.
    config = _config(tmp_path, app_database=f"fabp_contract_{uuid.uuid4().hex[:12]}")
    cls = load_backend_class(request.param, BUILTIN_DATABASES, "database")
    backend = cls(config, MagicMock())
    await backend.connect()
    try:
        yield backend
    finally:
        await _drop(backend)
        await backend.close()


async def _drop(backend) -> None:
    """Remove what the run created. Your own backend can define ``drop_database()``."""
    if hasattr(backend, "drop_database"):
        await backend.drop_database()
    elif getattr(backend, "db_name", None) and hasattr(backend.client, "drop_database"):
        await backend.client.drop_database(backend.db_name)  # MongoDB


@pytest.fixture(params=_selected("CONTRACT_CACHES", "memory"))
async def cache(request, tmp_path):
    """A connected cache backend and a key prefix unique to this test."""
    config = _config(tmp_path)
    cls = load_backend_class(request.param, BUILTIN_CACHES, "cache")
    backend = cls(config, MagicMock())
    await backend.connect()
    prefix = f"contract:{uuid.uuid4().hex[:12]}:"
    try:
        yield backend, prefix
    finally:
        await backend.delete_prefix(prefix)
        await backend.close()
