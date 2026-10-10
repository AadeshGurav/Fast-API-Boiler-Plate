"""Logging on top of the standard library.

* Console: one readable line per record, extras appended as ``key=value``.
* File (``log_to_file``): JSON lines in ``<logs_path>/app.log``, size-rotated. Records go
  through a queue and are written by a background thread, so logging never blocks the
  event loop on disk I/O.
* Every record carries the current request id (see :func:`set_request_id`).

``extra={...}`` fields are kept under ``extra_fields`` so arbitrary keys can never collide
with the attributes the ``logging`` module reserves.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import queue
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from config import Config

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_request_id(request_id: str | None) -> None:
    """Tag every log record emitted in this context with ``request_id``."""
    request_id_var.set(request_id)


def create_log_context(**fields: Any) -> dict[str, Any]:
    """``extra`` dict without the entries whose value is None."""
    return {key: value for key, value in fields.items() if value is not None}


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def _one_line(text: str) -> str:
    """Escape line breaks so request-controlled text cannot forge a second log record."""
    return text.replace("\r", "\\r").replace("\n", "\\n")


class _ConsoleFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        stamp = datetime.fromtimestamp(record.created, UTC).strftime("%H:%M:%S")
        line = f"{record.levelname:<8} | {stamp} | {_one_line(record.getMessage())}"
        extras = getattr(record, "extra_fields", None)
        if extras:
            line += " | " + " ".join(f"{k}={_one_line(str(v))}" for k, v in extras.items())
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "location": f"{record.pathname}:{record.lineno}",
            **(getattr(record, "extra_fields", None) or {}),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


class Logger:
    """Application logger with ``debug/info/warning/error/critical/exception``."""

    def __init__(self, config: Config) -> None:
        self.name: str = config["app_title"]
        level = config["log_level"]
        self._logger = logging.getLogger(self.name)
        self._logger.setLevel(logging.getLevelName(level) if isinstance(level, str) else level)
        self._logger.propagate = False
        self._listener: logging.handlers.QueueListener | None = None

        for handler in list(self._logger.handlers):  # rebuilt apps must not stack handlers
            self._logger.removeHandler(handler)

        # Every handler sits behind one queue and is written by a background thread, so a
        # slow terminal or disk never stalls a request; only cheap record capture happens
        # on the caller's side.
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(_ConsoleFormatter())
        handlers: list[logging.Handler] = [console]

        if config["log_to_file"]:
            path = Path(config["logs_path"])
            path.mkdir(parents=True, exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                path / "app.log",
                maxBytes=config["log_max_bytes"],
                backupCount=config["log_backup_count"],
                encoding="utf-8",
            )
            file_handler.setFormatter(_JsonFormatter())
            handlers.append(file_handler)

        records: queue.SimpleQueue = queue.SimpleQueue()
        queue_handler = logging.handlers.QueueHandler(records)
        queue_handler.addFilter(_RequestIdFilter())  # runs in the caller's context
        self._listener = logging.handlers.QueueListener(records, *handlers)
        self._listener.start()
        self._logger.addHandler(queue_handler)

    def _log(
        self, level: int, msg: str, *args: Any, exc_info: Any = None, extra: dict | None = None
    ) -> None:
        self._logger.log(
            level,
            msg,
            *args,
            exc_info=exc_info,
            extra={"extra_fields": extra} if extra else None,
            stacklevel=3,
        )

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.ERROR, msg, *args, **kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.CRITICAL, msg, *args, **kwargs)

    def exception(self, msg: str, *args: Any, exc_info: Any = True, **kwargs: Any) -> None:
        self._log(logging.ERROR, msg, *args, exc_info=exc_info, **kwargs)

    def shutdown(self) -> None:
        """Flush queued records to disk and stop the writer thread."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None


__all__ = ["Logger", "create_log_context", "request_id_var", "set_request_id"]
