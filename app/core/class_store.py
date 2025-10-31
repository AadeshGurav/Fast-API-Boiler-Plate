from __future__ import annotations
import importlib
import pkgutil
import threading
import weakref
from collections.abc import Callable
from typing import Any, TypeVar

from app.services.logger import Logger

T = TypeVar("T")


class ClassStore:
    """A class store for registering and retrieving classes and types."""

    _instance: type | None = None
    _instance_lock: threading.Lock = threading.Lock()

    def __new__(
        cls, config: dict[str, Any] | None = None, logger: Logger | None = None
    ) -> type:
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.__init__(config=config, logger=logger)
        return cls._instance

    def __init__(self, config: dict[str, Any] | None, logger: Logger | None) -> None:
        # core registries
        self._registry: dict[str, type] = {}
        self._metadata: dict[str, dict[str, Any]] = {}
        # cache for singleton instances or factories
        # use weakref to avoid memory leaks
        self._instances = weakref.WeakValueDictionary()
        self._factories: dict[str, Callable[..., Any]] = {}
        # thread lock for safety
        self._lock: threading.RLock = threading.RLock()

        # config and logger
        self._config: dict[str, Any] | None = config
        self._logger: Logger | None = logger

    def register(
        self,
        name: str | None = None,
        interfaces: list[type] | None = None,
        factory: Callable[..., Any] | None = None,
        **meta,
    ) -> Callable[[type], type]:
        """Decorator or direct call to register a class/type.

        Args:
            name: identifier in the registry
            interfaces: list of interfaces this implementation fulfills
            factory: optional custom factory for instantiation
            meta: any extra metadata to attach

        Returns:
            Decorator function that registers the class/type.

        """

        def decorator(cls: type) -> type:
            key = name or cls.__name__
            with self._lock:
                if key in self._registry:
                    raise KeyError(f"Duplicate registration: {key}")
                self._registry[key] = cls
                self._metadata[key] = {**meta, "interfaces": interfaces or []}
                if factory:
                    self._factories[key] = factory
            return cls

        return decorator

    def discover_services(self, packages: list[str]) -> None:
        """Scan given package paths, import modules to fire decorators/metaclasses.
        Lazy imports avoid upfront instantiation cost.
        """
        for pkg in packages:
            module = importlib.import_module(pkg)
            for finder, name, ispkg in pkgutil.walk_packages(
                module.__path__, module.__name__ + "."
            ):
                try:
                    importlib.import_module(name)
                except Exception:
                    # ignore faulty modules; log if desired
                    continue

    def get(self, identifier: str, *, singleton: bool = True, **context) -> Any:
        """Retrieve an instance by identifier. Optionally as singleton.
        Pass context into factory/constructor.
        """
        with self._lock:
            cls = self._registry.get(identifier)
            if not cls:
                raise KeyError(f"No class registered under '{identifier}'")
            if singleton:
                inst = self._instances.get(identifier)
                if inst:
                    return inst
            factory = self._factories.get(identifier) or cls
            instance = factory(**context)
            if singleton:
                self._instances[identifier] = instance
            return instance

    def get_by_interface(self, interface: type[T], **context) -> T:
        """Resolve a single implementation for given interface.
        Raises if zero or multiple found.
        """
        matches = [
            key
            for key, md in self._metadata.items()
            if interface in md.get("interfaces", [])
        ]
        if len(matches) == 0:
            raise LookupError(f"No implementation for interface {interface}")
        if len(matches) > 1:
            raise LookupError(f"Multiple implementations: {matches}")
        return self.get(matches[0], **context)

    def get_all_implementing(self, interface: type, **context) -> list[Any]:
        """Return all instances implementing given interface."""
        keys = [
            key
            for key, md in self._metadata.items()
            if interface in md.get("interfaces", [])
        ]
        return [self.get(key, singleton=False, **context) for key in keys]


__all__ = ["ClassStore"]
__all__ = ["ClassStore"]
