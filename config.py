"""Configuration loader: TOML files + ``.env`` + environment, validated by ``app.settings``.

``Config`` is a read-only mapping of every setting (defaults filled in), so callers use
``config["app_port"]`` / ``config.get("app_port")`` or attribute access. See
``app/settings.py`` for the list, the order of precedence and the meaning of each setting.
"""

from __future__ import annotations

import difflib
import json
import logging
import os
import secrets
import tomllib
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.settings import MIN_JWT_SECRET_LENGTH, Settings

logger = logging.getLogger(__name__)

ENV_PREFIX = "FABP_"
CONFIG_FILES = ("config.toml", "config.local.toml", "config.secrets.toml")
SECRETS_FILE = "config.secrets.toml"


class ConfigError(ValueError):
    """The configuration is invalid; the message lists every problem and where it came from."""


class Config(Mapping):
    """Validated, read-only view of all settings."""

    def __init__(self, config_dir: Path | str | None = None) -> None:
        self.config_dir = Path(config_dir) if config_dir else Path.cwd()
        self.origins: dict[str, str] = {}
        self.settings: Settings
        self.data: dict[str, Any] = {}
        self.reload()

    # ---- loading ------------------------------------------------------------------
    def _sources(self) -> list[tuple[str, dict[str, Any]]]:
        """(origin, values) in precedence order, lowest first."""
        sources: list[tuple[str, dict[str, Any]]] = []
        for name in CONFIG_FILES:
            path = self.config_dir / name
            if path.is_file():
                try:
                    sources.append((name, tomllib.loads(path.read_text(encoding="utf-8"))))
                except tomllib.TOMLDecodeError as e:
                    raise ConfigError(f"{name}: not valid TOML: {e}") from e

        env_file = self.config_dir / ".env"
        if env_file.is_file():
            sources.append((".env", self._parse_env_pairs(self._read_env_file(env_file))))
        sources.append(("environment", self._parse_env_pairs(os.environ)))
        return sources

    @staticmethod
    def _read_env_file(path: Path) -> dict[str, str]:
        values: dict[str, str] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                values[key.strip().removeprefix("export ")] = value.strip().strip("\"'")
        return values

    @staticmethod
    def _parse_env_pairs(pairs: Mapping[str, str]) -> dict[str, Any]:
        """``FABP_FOO=bar`` -> ``{"foo": "bar"}``; JSON for lists/objects."""
        parsed: dict[str, Any] = {}
        for name, raw in pairs.items():
            if not name.startswith(ENV_PREFIX) or len(name) == len(ENV_PREFIX):
                continue
            text = raw.strip()
            if text[:1] in "[{":
                try:
                    parsed[name[len(ENV_PREFIX) :].lower()] = json.loads(text)
                    continue
                except json.JSONDecodeError as e:
                    raise ConfigError(f"{name}: expected JSON ({e})") from e
            parsed[name[len(ENV_PREFIX) :].lower()] = raw
        return parsed

    def reload(self) -> None:
        """Re-read every source and re-validate."""
        merged: dict[str, Any] = {}
        origins: dict[str, str] = {}
        for origin, values in self._sources():
            for key, value in values.items():
                merged[key] = value
                origins[key] = origin
        try:
            settings = Settings.model_validate(merged)
        except ValidationError as e:
            raise ConfigError(self._explain(e, origins)) from e
        self.settings = settings
        self.data = settings.model_dump()
        self.origins = origins

    @staticmethod
    def _explain(error: ValidationError, origins: dict[str, str]) -> str:
        known = list(Settings.model_fields)
        lines = []
        for item in error.errors():
            key = str(item["loc"][0]) if item["loc"] else "?"
            where = origins.get(key, "defaults")
            if item["type"] == "extra_forbidden":
                hint = difflib.get_close_matches(key, known, n=1)
                suffix = f" Did you mean '{hint[0]}'?" if hint else ""
                lines.append(f"  - unknown setting '{key}' (from {where}).{suffix}")
            else:
                path = ".".join(str(p) for p in item["loc"])
                lines.append(f"  - {path} (from {where}): {item['msg']}")
        return "\n".join(lines)

    # ---- secrets --------------------------------------------------------------------
    def ensure_secret(self, key: str = "jwt_secret", nbytes: int = 64) -> bool:
        """Generate and persist a random secret under ``key`` if none is configured.

        Secrets must never live in the repository, but a fresh clone should still start.
        The value goes to ``config.secrets.toml`` (git-ignored, mode 0600) so every worker
        and restart sees the same one. In containers mount that file or set
        ``FABP_JWT_SECRET``; otherwise a rebuilt container generates a new secret and
        existing tokens stop validating.

        Returns:
        -------
            True if a new secret was generated.

        """
        if self.data.get(key):
            return False
        path = self.config_dir / SECRETS_FILE
        existing = tomllib.loads(path.read_text()) if path.exists() else {}
        existing[key] = secrets.token_urlsafe(nbytes)
        path.write_text("".join(f'{k} = "{v}"\n' for k, v in existing.items()), encoding="utf-8")
        path.chmod(0o600)
        self.reload()
        logger.info("Generated %s in %s (git-ignored).", key, path)
        return True

    # ---- mapping interface ------------------------------------------------------------
    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def __getattr__(self, name: str) -> Any:
        """Attribute access (``config.app_port``). Unknown names raise, never return None."""
        if name != "data" and name in self.data:
            return self.data[name]
        raise AttributeError(f"Configuration key '{name}' not found")

    def __repr__(self) -> str:
        return f"Config({self.config_dir}, {len(self.data)} settings)"


__all__ = ["MIN_JWT_SECRET_LENGTH", "Config", "ConfigError"]
