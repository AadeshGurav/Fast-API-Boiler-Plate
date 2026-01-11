from __future__ import annotations

import importlib
import pkgutil
import sys
import threading
import traceback
import weakref
from collections.abc import Callable
from typing import Any, TypeVar

from app.services.logger import Logger

T = TypeVar("T")

# Global fallback instance for when DI container is not available
_fallback_instance: ClassStore | None = None
_fallback_lock: threading.Lock = threading.Lock()


class ClassStore:
    """A class store for registering and retrieving classes and types."""

    def __init__(
        self: ClassStore,
        config: dict[str, Any] | None = None,
        logger: Logger | None = None,
    ) -> None:
        """Initialize the ClassStore instance.

        Args:
        ----
            config: configuration dictionary
            logger: logger instance

        """
        # core registries
        self._registry: dict[str, type] = {}
        self._metadata: dict[str, dict[str, Any]] = {}
        # track which classes should be singletons
        self._singleton_registry: dict[str, bool] = {}
        # cache for singleton instances or factories
        # use weakref to avoid memory leaks
        self._instances = weakref.WeakValueDictionary()
        self._factories: dict[str, Callable[..., Any]] = {}
        # thread lock for safety
        self._lock: threading.RLock = threading.RLock()

        # config and logger
        self._config: dict[str, Any] | None = config
        self._logger: Logger | None = logger
        # container reference for service access (lazy-loaded)
        self._container: Any = None

    def register(
        self: ClassStore,
        name: str | None = None,
        interfaces: list[type] | None = None,
        factory: Callable[..., Any] | None = None,
        singleton: bool = True,
        **meta: dict[str, Any],
    ) -> Callable[[type], type]:
        """Decorator or direct call to register a class/type.

        Args:
        ----
            name: identifier in the registry
            interfaces: list of interfaces this implementation fulfills
            factory: optional custom factory for instantiation
            singleton: whether instances should be singletons (default: True)
            meta: any extra metadata to attach

        Returns:
        -------
            Decorator function that registers the class/type.

        """
        if not isinstance(singleton, bool):
            raise TypeError("singleton parameter must be a boolean")

        def decorator(cls: type) -> type:
            if not isinstance(cls, type):
                raise TypeError(f"Expected a class, got {type(cls)}")
            key = name or cls.__name__
            with self._lock:
                # Allow re-registration if it's the same class (for discovery)
                if key in self._registry:
                    if self._registry[key] is cls:
                        # Same class already registered, skip
                        if self._logger:
                            self._logger.debug(
                                f"Class '{key}' already registered, skipping",
                                extra={"class_name": key},
                            )
                        return cls
                    # Different class with same key, raise error
                    raise KeyError(f"Duplicate registration: {key}")
                self._registry[key] = cls
                self._singleton_registry[key] = singleton
                self._metadata[key] = {**meta, "interfaces": interfaces or []}
                if factory:
                    if not callable(factory):
                        raise TypeError("factory must be callable")
                    self._factories[key] = factory
                if self._logger:
                    self._logger.debug(
                        f"Registered class '{key}' (singleton={singleton})",
                        extra={"class_name": key, "singleton": singleton},
                    )
            return cls

        return decorator

    def discover_services(self: ClassStore, packages: list[str]) -> None:
        """Scan given package paths, import modules to fire decorators/metaclasses.
        Lazy imports avoid upfront instantiation cost.

        Args:
        ----
            packages: list of package paths to scan

        Returns:
        -------
            None

        """
        if not packages:
            return

        initial_count = len(self._registry)
        discovered_count = 0
        failed_count = 0

        if self._logger:
            self._logger.info(
                f"Starting discovery for {len(packages)} package(s)",
                extra={"packages": packages, "initial_registry_size": initial_count},
            )

        for pkg in packages:
            if not isinstance(pkg, str) or not pkg:
                if self._logger:
                    self._logger.warning(
                        f"Invalid package name: {pkg}", extra={"package": pkg}
                    )
                continue

            try:
                if self._logger:
                    self._logger.debug(
                        f"Scanning package: {pkg}", extra={"package": pkg}
                    )
                module = importlib.import_module(pkg)
                if not hasattr(module, "__path__"):
                    if self._logger:
                        self._logger.debug(
                            f"Package '{pkg}' has no __path__, skipping",
                            extra={"package": pkg},
                        )
                    continue

                for finder, name, ispkg in pkgutil.walk_packages(
                    module.__path__, module.__name__ + "."
                ):
                    try:
                        # Force re-import to ensure decorators run with correct instance
                        if name in sys.modules:
                            del sys.modules[name]
                        importlib.import_module(name)
                        discovered_count += 1
                        if self._logger:
                            self._logger.debug(
                                f"Successfully imported module: {name}",
                                extra={"module": name, "is_package": ispkg},
                            )
                    except ImportError as e:
                        failed_count += 1
                        if self._logger:
                            self._logger.warning(
                                f"Failed to import module '{name}': {e}",
                                extra={"module": name, "error": str(e)},
                            )
                    except SyntaxError as e:
                        failed_count += 1
                        if self._logger:
                            self._logger.error(
                                f"Syntax error in module '{name}': {e}",
                                extra={
                                    "module": name,
                                    "error": str(e),
                                    "filename": getattr(e, "filename", None),
                                    "lineno": getattr(e, "lineno", None),
                                },
                            )
                    except (AttributeError, TypeError, ValueError) as e:
                        failed_count += 1
                        if self._logger:
                            self._logger.error(
                                f"Unexpected error importing module '{name}': {e}",
                                extra={
                                    "module": name,
                                    "error": str(e),
                                    "error_type": type(e).__name__,
                                    "traceback": traceback.format_exc(),
                                },
                            )
                    except BaseException as e:
                        failed_count += 1
                        if self._logger:
                            self._logger.error(
                                f"Unexpected error importing module '{name}': {e}",
                                extra={
                                    "module": name,
                                    "error": str(e),
                                    "error_type": type(e).__name__,
                                    "traceback": traceback.format_exc(),
                                },
                            )
                        raise
            except ImportError as e:
                failed_count += 1
                if self._logger:
                    self._logger.warning(
                        f"Failed to import package '{pkg}': {e}",
                        extra={"package": pkg, "error": str(e)},
                    )
            except (AttributeError, TypeError, ValueError) as e:
                failed_count += 1
                if self._logger:
                    self._logger.error(
                        f"Unexpected error scanning package '{pkg}': {e}",
                        extra={
                            "package": pkg,
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "traceback": traceback.format_exc(),
                        },
                    )
            except BaseException as e:
                failed_count += 1
                if self._logger:
                    self._logger.error(
                        f"Unexpected error scanning package '{pkg}': {e}",
                        extra={
                            "package": pkg,
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "traceback": traceback.format_exc(),
                        },
                    )
                raise

        final_count = len(self._registry)
        newly_registered = final_count - initial_count

        if self._logger:
            self._logger.info(
                f"Discovery completed: {newly_registered} new classes registered, "
                f"{discovered_count} modules imported, {failed_count} failures",
                extra={
                    "initial_count": initial_count,
                    "final_count": final_count,
                    "newly_registered": newly_registered,
                    "modules_imported": discovered_count,
                    "failures": failed_count,
                },
            )

    def _get_container(self: ClassStore) -> Any:
        """Get container reference (lazy-loaded).

        Returns
        -------
            Container instance or None if not available.

        """
        if self._container is None:
            try:
                from app import container

                if container is not None:
                    self._container = container
            except ImportError:
                pass
            except (AttributeError, TypeError, ValueError):
                pass
        return self._container

    def get_service(self: ClassStore, service_name: str) -> Any:
        """Get a service from the DI container.

        Args:
        ----
            service_name: name of the service to retrieve (e.g., 'data_service', 'logger')

        Returns:
        -------
            Service instance.

        Raises:
        ------
            LookupError: if service is not found or container is not available.

        """
        container = self._get_container()
        if container is None:
            raise LookupError(
                f"Cannot retrieve service '{service_name}': container not available"
            )

        try:
            service = getattr(container, service_name, None)
            if service is None:
                raise LookupError(f"Service '{service_name}' not found in container")
            if callable(service):
                return service()
            return service
        except Exception as e:
            if self._logger:
                self._logger.error(
                    f"Failed to retrieve service '{service_name}': {e}",
                    extra={"service_name": service_name, "error": str(e)},
                )
            raise LookupError(
                f"Failed to retrieve service '{service_name}': {e}"
            ) from e

    def _inject_common_services(
        self: ClassStore, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Inject common services into context if not already present.

        Args:
        ----
            context: existing context dictionary

        Returns:
        -------
            Updated context with common services injected.

        """
        container = self._get_container()
        if container is None:
            return context

        # Common services to auto-inject
        common_services = ["data_service", "logger", "config"]
        injected = {}

        for service_name in common_services:
            if service_name not in context:
                try:
                    service = self.get_service(service_name)
                    injected[service_name] = service
                except LookupError:
                    pass

        return {**context, **injected}

    def get(
        self: ClassStore,
        identifier: str,
        *,
        singleton: bool | None = None,
        **context: dict[str, Any],
    ) -> Any:
        """Retrieve an instance by identifier. Optionally as singleton.
        Pass context into factory/constructor. Common services are auto-injected.

        Args:
        ----
            identifier: identifier of the class to retrieve
            singleton: whether to return a singleton instance (None = use registration default)
            context: context to pass into the factory/constructor

        Returns:
        -------
            Instance of the class.

        """
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("identifier must be a non-empty string")

        with self._lock:
            cls = self._registry.get(identifier)
            if not cls:
                raise KeyError(f"No class registered under '{identifier}'")

            # Use registration default if singleton not explicitly specified
            if singleton is None:
                singleton = self._singleton_registry.get(identifier, True)

            if singleton:
                inst = self._instances.get(identifier)
                if inst is not None:
                    return inst

            # Auto-inject common services if not in context
            enhanced_context = self._inject_common_services(context)

            factory = self._factories.get(identifier) or cls
            try:
                instance = factory(**enhanced_context)
            except Exception as e:
                if self._logger:
                    self._logger.error(
                        f"Failed to instantiate '{identifier}': {e}",
                        extra={
                            "identifier": identifier,
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "context_keys": list(enhanced_context.keys()),
                        },
                    )
                raise

            if singleton:
                self._instances[identifier] = instance

            return instance

    def get_by_interface(
        self: ClassStore, interface: type[T], **context: dict[str, Any]
    ) -> T:
        """Resolve a single implementation for given interface.
        Raises if zero or multiple found.

        Args:
        ----
            interface: interface to resolve
            context: context to pass into the factory/constructor

        Returns:
        -------
            Instance of the class.

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

    def get_all_implementing(
        self: ClassStore, interface: type, **context: dict[str, Any]
    ) -> list[Any]:
        """Return all instances implementing given interface.

        Args:
        ----
            interface: interface to resolve
            context: context to pass into the factory/constructor

        Returns:
        -------
            List of instances of the class.

        """
        keys = [
            key
            for key, md in self._metadata.items()
            if interface in md.get("interfaces", [])
        ]
        return [self.get(key, singleton=False, **context) for key in keys]


def get_class_store() -> ClassStore:
    """Get ClassStore instance from DI container or create fallback instance.

    This function provides a module-level accessor for ClassStore that:
    1. First tries to get the instance from the DI container
    2. Falls back to a global singleton instance if container is not available
    3. Creates a new instance only if neither is available

    Returns
    -------
        ClassStore instance.

    """
    global _fallback_instance

    # Try to get from DI container first
    try:
        from app import container

        if container is not None:
            try:
                instance = container.class_store()
                if instance is not None:
                    return instance
            except (AttributeError, TypeError, ValueError):
                pass
    except ImportError:
        pass
    except (AttributeError, TypeError, ValueError):
        pass

    # Fallback to global singleton
    if _fallback_instance is None:
        with _fallback_lock:
            if _fallback_instance is None:
                _fallback_instance = ClassStore()

    return _fallback_instance


__all__ = ["ClassStore", "get_class_store"]
