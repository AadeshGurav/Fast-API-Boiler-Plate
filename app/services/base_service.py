from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.logger import Logger
    from config import Config


class BaseService:
    """Base service class for all services."""

    def __init__(
        self: BaseService,
        config: Config,
        logger: Logger,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize BaseService.

        Args:
        ----
            config: Configuration object.
            logger: Logger instance.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        """
        self.logger: Logger = logger
        self.config: Config = config

        for key, value in kwargs.items():
            setattr(self, key, value)

        for arg in args:
            setattr(self, arg, arg)
