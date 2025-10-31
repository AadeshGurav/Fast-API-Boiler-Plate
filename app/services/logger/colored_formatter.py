"""Colored formatter for console output."""

from __future__ import annotations

from datetime import datetime
from logging import CRITICAL, DEBUG, ERROR, INFO, WARNING, Formatter, LogRecord

from colorama import Fore, Style
from colorama import init as colorama_init

colorama_init(autoreset=True)


class ColoredFormatter(Formatter):
    """Human-friendly colored formatter for console output."""

    LEVEL_COLORS = {
        DEBUG: Fore.CYAN,
        INFO: Fore.GREEN,
        WARNING: Fore.YELLOW,
        ERROR: Fore.RED,
        CRITICAL: Fore.MAGENTA,
    }

    def __init__(self: ColoredFormatter, fmt: str | None = None) -> None:
        """Initialize ColoredFormatter.

        Args:
        ----
            fmt: Format string for the log message.

        """
        super().__init__(
            fmt or "%(levelname)s | %(asctime)s | %(name)s:%(lineno)d | %(message)s"
        )

    def format(self: ColoredFormatter, record: LogRecord) -> str:
        """Format the log record.

        Args:
        ----
            record: Log record to format.

        Returns:
        -------
            Formatted log record.

        """
        color = self.LEVEL_COLORS.get(record.levelno, "")
        timestamp = datetime.utcnow().strftime("%H:%M:%S")
        level_text = f"{record.levelname:<8}"
        name = f"{record.name}:{record.lineno}"
        msg = record.getMessage()
        return f"{color}{level_text}{Style.RESET_ALL} | {timestamp} | {name} | {msg}"
