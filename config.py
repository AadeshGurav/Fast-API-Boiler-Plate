"""Simple configuration loader from JSON files."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


class Config(dict):
    """Simple configuration loader from JSON files.

    Supports global and local JSON files with priority handling.
    """

    def __init__(self: Config, config_dir: Path | str | None = None) -> None:
        """Initialize the Config class.

        Args:
        ----
            config_dir: The directory containing the configuration files.

        """
        super().__init__()
        self.data: dict[str, Any] = {}
        self.config_dir: Path = (
            Path(config_dir) if config_dir else Path.cwd() / "config.d"
        )

        if not self.config_dir.exists():
            self.config_dir.mkdir(exist_ok=True)
            self._update_gitignore()

        self.reload()

    def _update_gitignore(self: Config) -> None:
        """Add config.d/*-local.json to .gitignore if not present."""
        gitignore_path = Path.cwd() / ".gitignore"
        ignore_entry = "config.d/*-local.json"

        if gitignore_path.exists():
            content = gitignore_path.read_text()
            if ignore_entry not in content:
                with gitignore_path.open("a") as f:
                    if not content.endswith("\n"):
                        f.write("\n")
                    f.write(f"{ignore_entry}\n")
                logger.info(f"Added {ignore_entry} to .gitignore")

    def _load_config(self: Config) -> None:
        """Load all JSON configuration files with global/local priority."""
        global_configs: dict[str, Any] = {}
        local_configs: dict[str, Any] = {}
        regular_configs: dict[str, Any] = {}

        for file_path in self.config_dir.glob("*.json"):
            if not file_path.is_file():
                continue

            file_name = file_path.stem

            try:
                with file_path.open("r") as f:
                    file_data = json.load(f)
                    if "-local" in file_name:
                        local_configs.update(file_data)
                        logger.debug(f"Loaded local config: {file_path}")
                    elif "-global" in file_name:
                        global_configs.update(file_data)
                        logger.debug(f"Loaded global config: {file_path}")
                    else:
                        regular_configs.update(file_data)
                        logger.debug(f"Loaded config: {file_path}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON file {file_path}: {e}")

        # Merge configs: regular < global < local
        self.data = {**regular_configs, **global_configs, **local_configs}

        if not self.data:
            logger.warning(f"No configuration files found in {self.config_dir}")

    def reload(self: Config) -> None:
        """Reload all configuration files."""
        self.data.clear()
        self._load_config()

    def __getitem__(self: Config, key: str) -> Any:
        """Return value for key, raise KeyError if missing.

        Args:
        ----
            key: The key to get the value for.

        Returns:
        -------
            The value for the key.

        """
        if key in self.data:
            return self.data[key]
        raise KeyError(f"Configuration key '{key}' not found")

    def get(self: Config, key: str, default: Any = None) -> Any:
        """Return value for key, or default if missing.

        Args:
        ----
            key: The key to get the value for.
            default: The default value to return if the key is not found.

        Returns:
        -------
            The value for the key or the default value if the key is not found.

        """
        return self.data.get(key, default)

    def __getattr__(self: Config, name: str) -> Any:
        """Allow attribute-style access to config keys.

        Args:
        ----
            name: The name of the attribute to get the value for.

        Returns:
        -------
            The value for the attribute.

        """
        if name in self.data:
            return self.data[name]
        # Fall back to normal attribute access
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return None

    def hasattr(self: Config, name: str) -> bool:
        """Check if config key exists.

        Args:
        ----
            name: The name of the attribute to check.

        Returns:
        -------
            True if the attribute exists in the config data or in the super class, False otherwise.

        """
        return name in self.data or hasattr(super(), name)


__all__ = ["Config"]
