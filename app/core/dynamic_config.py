"""Dynamic configuration base class combining Pydantic validation with JSON flexibility."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from config import Config

T = TypeVar("T", bound="DynamicConfig")


class DynamicConfig(BaseModel):
    """Base class combining Pydantic validation with JSON config flexibility.

    This class enables models to load configuration from JSON files via the existing
    Config class while maintaining Pydantic's validation trust. All RBAC models
    (Role, Permission, Group) extend this for JSON-driven runtime updates.
    """

    @classmethod
    def load_from_config(cls: type[T], config: Config, config_key: str) -> T:
        """Load configuration from existing Config instance (uses config.py).

        Args:
        ----
            config: The Config instance to load from
            config_key: The key in the config to load

        Returns:
        -------
            Instance of the class loaded with config data

        """
        data = config.get(config_key, {})
        return cls(**data)

    def reload_from_config(
        self: DynamicConfig, config: Config, config_key: str
    ) -> None:
        """Hot-reload: update instance from Config without recreating.

        Args:
        ----
            config: The Config instance to reload from
            config_key: The key in the config to reload

        """
        data = config.get(config_key, {})
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @classmethod
    def load_from_json_file(cls: DynamicConfig, file_path: str) -> DynamicConfig:
        """Load configuration directly from JSON file.

        Args:
        ----
            file_path: Path to the JSON file

        Returns:
        -------
            Instance of the class loaded with file data

        """
        import json

        with open(file_path) as f:
            data = json.load(f)
        return cls(**data)

    def reload_from_json_file(self: DynamicConfig, file_path: str) -> None:
        """Hot-reload: update instance from JSON file without recreating.

        Args:
        ----
            file_path: Path to the JSON file

        """
        import json

        with open(file_path) as f:
            data = json.load(f)
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)


__all__ = ["DynamicConfig"]
