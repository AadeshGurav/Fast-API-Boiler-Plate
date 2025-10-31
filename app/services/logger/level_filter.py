"""Level filter for logging."""

from __future__ import annotations

from logging import Filter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from logging import LogRecord


class LevelFilter(Filter):
    """Allow only records with exact matching level (helps prevent duplication)."""

    def __init__(self: LevelFilter, level: int) -> None:
        """Initialize LevelFilter.

        Args:
        ----
            level: Level to filter.

        """
        super().__init__()
        self.level: int = level

    def filter(self: LevelFilter, record: LogRecord) -> bool:
        """Filter the log record.

        Args:
        ----
            record: Log record to filter.

        Returns:
        -------
            True if the log record matches the level, False otherwise.

        """
        return record.levelno == self.level


__all__ = ["LevelFilter"]
