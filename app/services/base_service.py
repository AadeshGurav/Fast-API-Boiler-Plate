from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.logger import Logger
    from config import Config


class BaseService:
    """Base service class for all services."""

    _instance: BaseService | None = None
    _initialized: bool = False

    def __new__(
        cls: BaseService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> BaseService:
        """Create a new Logger instance.

        Args:
        ----
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
        -------
            Logger instance.

        """
        if cls._instance is None:
            cls._instance: cls = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(
        self: BaseService,
        config: Config,
        logger: Logger,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize BaseService.

        Args:
        ----
            config: Configuration object.
            logger: Logger instance.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        """
        if self._initialized:
            return

        self.logger: Logger = logger
        self.config: Config = config

        for key, value in kwargs.items():
            setattr(self, key, value)

        for arg in args:
            setattr(self, arg, arg)
        self._initialized = True
