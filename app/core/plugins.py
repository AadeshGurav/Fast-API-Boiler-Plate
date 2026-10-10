"""Resolve a configured provider name to a backend class (bring-your-own backends).

A provider is either a built-in name (``"redis"``, ``"mongodb"``) or a dotted path to your
own class, ``"my_package.my_module:MyCache"``. The class must implement the matching
interface (``CacheInterface``, ``DatabaseInterface``); it is constructed with
``(config, logger)``.
"""

from __future__ import annotations

import importlib
from typing import Any


def load_backend_class(provider: str | None, builtin: dict[str, str], kind: str) -> type[Any]:
    """The class for ``provider``.

    Args:
    ----
        provider: Built-in name or ``module:Class`` path.
        builtin: Built-in provider name -> ``module:Class``.
        kind: What is being loaded ("cache", "database"), for error messages.

    Raises:
    ------
        ValueError: If the provider is unknown or cannot be imported.

    """
    target = builtin.get(provider or "", provider or "")
    if ":" not in target:
        raise ValueError(
            f"Unknown {kind} provider {provider!r}. Use one of {sorted(builtin)} or "
            "'package.module:ClassName' for your own implementation."
        )
    module_name, _, class_name = target.partition(":")
    try:
        return getattr(importlib.import_module(module_name), class_name)
    except (ImportError, AttributeError) as e:
        raise ValueError(f"Cannot load {kind} provider {target!r}: {e}") from e
