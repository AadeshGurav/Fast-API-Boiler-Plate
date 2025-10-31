"""Safe JSON formatter for logging."""

from __future__ import annotations

import json
import socket
from datetime import datetime
from typing import TYPE_CHECKING, Any

from colorama import init as colorama_init
from pythonjsonlogger import jsonlogger

from app.services.logger.utils import request_id_var

if TYPE_CHECKING:
    from logging import LogRecord

colorama_init(autoreset=True)


class SafeJsonFormatter(jsonlogger.JsonFormatter):
    """JSON formatter ensuring NDJSON and adding standard structured fields."""

    def __init__(
        self: SafeJsonFormatter,
        fmt: str = "%(message)s",
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize SafeJsonFormatter.

        Args:
        ----
            fmt: Format string for the log message.
            *args: Additional arguments for the formatter.
            **kwargs: Additional keyword arguments for the formatter.

        """
        self.hostname = socket.gethostname()
        super().__init__(fmt, *args, **kwargs)

    def default(self: SafeJsonFormatter, obj: Any) -> str:
        """Default method to handle serialization of objects.

        Args:
        ----
            obj: Object to serialize.

        Returns:
        -------
            Serialized object.

        """
        try:
            return str(obj)
        except Exception:  # noqa: BLE001
            return "<unserializable>"

    def add_fields(
        self: SafeJsonFormatter,
        log_record: dict[str, Any],
        record: LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        """Add fields to the log record.

        Args:
        ----
            log_record: Log record to add fields to.
            record: Record to add fields to.
            message_dict: Message dictionary to add fields to.

        """
        super().add_fields(log_record, record, message_dict)

        # Use setdefault to avoid overwriting if present
        log_record.setdefault(
            "timestamp", datetime.utcnow().isoformat(timespec="milliseconds")
        )
        log_record.setdefault("hostname", self.hostname)
        log_record.setdefault("service", "fastapi-app")
        log_record.setdefault("level", record.levelname)
        log_record.setdefault("logger_name", record.name)

        # request_id: prefer explicit on record, else contextvar
        rid = getattr(record, "request_id", None) or request_id_var.get()
        if rid:
            log_record["request_id"] = rid

        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            # merge any extra fields provided
            log_record.update(record.extra_fields)

    def format(self: SafeJsonFormatter, record: LogRecord) -> str:
        """Format the log record.

        Args:
        ----
            record: Log record to format.

        Returns:
        -------
            Formatted log record.

        """
        try:
            # process_log_record expects dict; rely on parent to create message dict
            msg_dict = self.process_log_record(record.__dict__)
            self.add_fields(msg_dict, record, record.__dict__)
            return json.dumps(msg_dict, default=self.default, ensure_ascii=False)
        except Exception as e:  # noqa: BLE001
            fallback = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": getattr(record, "levelname", "ERROR"),
                "message": f"Logging error: {e}",
            }
            return json.dumps(fallback, ensure_ascii=False)


__all__ = ["SafeJsonFormatter"]
