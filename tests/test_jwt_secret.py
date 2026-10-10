"""No JWT secret in the repo, but a fresh clone still starts."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from config import Config, ConfigError

REPO = Path(__file__).parent.parent


def test_repository_config_carries_no_jwt_secret():
    assert "jwt_secret" not in (REPO / "config.toml").read_text()


def test_secret_is_generated_once_and_persisted_privately(tmp_path):
    config = Config(config_dir=tmp_path)

    assert config.ensure_secret() is True
    first = config["jwt_secret"]
    assert Config(config_dir=tmp_path).ensure_secret() is False  # not regenerated

    assert len(first) >= 64 and Config(config_dir=tmp_path)["jwt_secret"] == first
    assert stat.S_IMODE((tmp_path / "config.secrets.toml").stat().st_mode) == 0o600


def test_configured_secret_is_left_alone(tmp_path):
    secret = "m" * 40
    (tmp_path / "config.local.toml").write_text(f'jwt_secret = "{secret}"\n')
    config = Config(config_dir=tmp_path)

    assert config.ensure_secret() is False and config["jwt_secret"] == secret


def test_config_behaves_like_a_mapping_and_rejects_unknown_attributes(tmp_path):
    config = Config(config_dir=tmp_path)

    assert config["app_port"] == 8000 and "app_port" in config and config.app_port == 8000
    assert dict(config)["mongo_host"] == "localhost" and len(config) > 100
    with pytest.raises(AttributeError):
        _ = config.typo_setting


def test_layers_override_in_documented_order(tmp_path, monkeypatch):
    (tmp_path / "config.toml").write_text(
        "app_port = 1111\napp_title = 'from-base'\nmongo_host = 'base'\n"
    )
    (tmp_path / "config.local.toml").write_text("app_port = 2222\nmongo_host = 'local'\n")
    (tmp_path / ".env").write_text("FABP_MONGO_HOST=dotenv\n# comment\nFABP_APP_DEBUG=true\n")
    monkeypatch.setenv("FABP_APP_PORT", "3333")
    config = Config(config_dir=tmp_path)

    assert config["app_title"] == "from-base"
    assert config["mongo_host"] == "dotenv"  # .env beats files
    assert config["app_port"] == 3333  # environment beats everything, coerced to int
    assert config["app_debug"] is True
    assert config.origins["app_port"] == "environment" and config.origins["mongo_host"] == ".env"


def test_debug_dependent_defaults(tmp_path):
    prod = Config(config_dir=tmp_path)
    (tmp_path / "config.local.toml").write_text("app_debug = true\n")
    dev = Config(config_dir=tmp_path)

    assert (prod["cookie_secure"], prod["csp_enabled"]) == (True, True)
    assert (dev["cookie_secure"], dev["csp_enabled"]) == (False, False)


def test_mistakes_fail_at_startup_with_a_helpful_message(tmp_path, monkeypatch):
    (tmp_path / "config.local.toml").write_text('mongo_hots = "x"\napp_port = "eighty"\n')
    with pytest.raises(ConfigError) as error:
        Config(config_dir=tmp_path)

    message = str(error.value)
    assert "unknown setting 'mongo_hots'" in message and "Did you mean 'mongo_host'" in message
    assert "app_port" in message and "config.local.toml" in message


def test_role_references_are_checked(tmp_path):
    (tmp_path / "config.local.toml").write_text('[rbac_roles.a]\ninherits = ["ghost"]\n')
    with pytest.raises(ConfigError, match="inherits unknown role 'ghost'"):
        Config(config_dir=tmp_path)


def test_several_workers_need_a_shared_cache(tmp_path):
    (tmp_path / "config.local.toml").write_text('app_workers = 4\napp_cache_provider = "memory"\n')
    with pytest.raises(ConfigError, match=r"per process.*app_workers = 4"):
        Config(config_dir=tmp_path)

    (tmp_path / "config.local.toml").write_text('app_workers = 4\napp_cache_provider = "redis"\n')
    assert Config(config_dir=tmp_path)["app_workers"] == 4


def test_toml_syntax_errors_name_the_file(tmp_path):
    (tmp_path / "config.local.toml").write_text("app_port = = 1\n")
    with pytest.raises(ConfigError, match=r"config\.local\.toml: not valid TOML"):
        Config(config_dir=tmp_path)


def test_generated_reference_is_current():
    from app.settings import reference_markdown

    assert (REPO / "docs" / "CONFIGURATION.md").read_text() == reference_markdown(), (
        "run `make config-docs` and commit docs/CONFIGURATION.md"
    )


def test_the_shipped_config_is_valid_and_documents_every_setting_it_sets():
    from app.settings import Settings

    config = Config(config_dir=REPO)
    assert set(config) == set(Settings.model_fields)


@pytest.mark.parametrize("key", ["jwt_secret", "mfa_encryption_key"])
def test_placeholder_and_short_keys_are_refused(key):
    from pydantic import ValidationError

    from app.settings import Settings

    for bad in ("change-me-generated-by-make-setup", "short"):
        with pytest.raises(ValidationError):
            Settings(**{key: bad})


def test_the_mfa_key_is_generated_alongside_the_jwt_secret(tmp_path):
    config = Config(config_dir=tmp_path)

    assert config.ensure_secret("mfa_encryption_key") is True
    assert Config(config_dir=tmp_path)["mfa_encryption_key"] == config["mfa_encryption_key"]
