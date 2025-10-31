from __future__ import annotations
from abc import ABC
from typing import TYPE_CHECKING, Any, Dict, Optional, Type

if TYPE_CHECKING:
    from app.services.logger.core import Logger


class BaseInterface(ABC):
    """Base Interface with per-subclass singleton pattern.

    Each subclass gets its own singleton instance, preventing
    instance sharing between different interface implementations.
    """

    _instances: Dict[Type, Optional["BaseInterface"]] = {}

    def __init_subclass__(cls: type["BaseInterface"], **kwargs: dict[str, Any]) -> None:
        """Initialize per-subclass singleton storage."""
        super().__init_subclass__(**kwargs)
        cls._instances[cls] = None

    def __new__(
        cls: type["BaseInterface"], *args: Any, **kwargs: Any
    ) -> "BaseInterface":
        """Create or return existing instance for the specific subclass."""
        # Ensure the subclass has its own instance storage
        if cls not in cls._instances:
            cls._instances[cls] = None

        # Create new instance if none exists for this specific class
        if cls._instances[cls] is None:
            cls._instances[cls] = super().__new__(cls)

        return cls._instances[cls]

    def __init__(
        self: "BaseInterface", logger: "Logger", config: dict, *args: Any, **kwargs: Any
    ) -> None:
        """Initialize only once per subclass instance."""
        # Prevent re-initialization of existing instances
        if hasattr(self, "_initialized"):
            return

        self.logger = logger
        self.config = config
        self._initialized = True
        self._initialized = True
