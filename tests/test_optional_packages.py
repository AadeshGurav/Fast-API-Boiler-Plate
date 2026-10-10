"""Optional packages: the app runs without them, and asks for them by name when needed."""

from __future__ import annotations

import sys

import pytest

from app.services.registry import build_services
from app.services.sentry import set_user
from config import Config


@pytest.mark.parametrize(
    ("flag", "module"), [("tracing_enabled", "opentelemetry"), ("sentry_enabled", "sentry_sdk")]
)
def test_enabling_a_feature_without_its_package_names_the_fix(tmp_path, monkeypatch, flag, module):
    for name in [m for m in sys.modules if m == module or m.startswith(module + ".")]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.setitem(sys.modules, module, None)  # makes "import <module>" fail
    config = Config(config_dir=tmp_path)
    config.data.update(
        {flag: True, "sentry_dsn": "https://key@example.invalid/1", "jwt_secret": "x" * 64}
    )

    with pytest.raises(RuntimeError, match=r"requirements-observability\.txt"):
        build_services(config)


def test_sentry_user_tagging_is_a_no_op_until_sentry_starts(monkeypatch):
    monkeypatch.delitem(sys.modules, "sentry_sdk", raising=False)

    set_user("user-1", "ada")  # must not import or fail
