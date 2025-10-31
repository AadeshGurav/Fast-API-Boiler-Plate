"""Advanced Logging Module.
=======================

This module provides a high-performance, context-aware logging system
for Python applications, including async frameworks like FastAPI.

It supports structured JSON logging in NDJSON format, making it easy
to ingest logs into ELK, Datadog, or other log management systems.

Logs include standard fields such as timestamp, hostname, service name,
level, logger name, and optional request_id propagated via contextvars.

The `Logger` class is a singleton, ensuring a single consistent logger
instance throughout the application.

It writes logs to both console and level-specific rotating files
(DEBUG, INFO, ERROR), preventing duplication and managing file rotation.

Console output is human-readable and color-coded per log level
for easy debugging.

File logging is async-friendly using `AsyncRotatingFileHandler`,
which queues logs and writes them in background threads to avoid
blocking the event loop.

For synchronous scripts or CLI tools, a threaded QueueListener
fallback is available to handle logs safely.

The module also supports log sampling for lower levels, reducing
log volume while always logging errors and higher-severity messages.

Request IDs can be set globally per request using `set_request_id`,
which automatically attaches the ID to all log entries in that context.

The `SafeJsonFormatter` ensures all log messages are JSON-serializable
and merges any extra fields provided.

`ColoredFormatter` handles console logs with timestamp, logger name,
line number, and colored levels.

`LevelFilter` ensures that each file handler only writes logs
matching its specific level.

The `Logger` class provides convenience methods such as `debug`,
`info`, `warning`, `error`, `critical`, and `exception`.

Async apps should call `enable_async()` during startup to start
background log writers, and `shutdown()` on exit to flush logs.

Sync scripts can use `enable_sync_fallback()` and `shutdown_sync()`
to achieve similar behavior without an event loop.

This module is designed to be DI-friendly but can be used
standalone with default settings.

It ensures reliable, structured logging in both async and sync Python
applications with minimal setup.
"""
from __future__ import annotations

# ruff: isort: skip_file

from .async_rotating_file_handler import AsyncRotatingFileHandler  # noqa
from .colored_formatter import ColoredFormatter  # noqa
from .level_filter import LevelFilter  # noqa
from .safe_json_formatter import SafeJsonFormatter  # noqa
from .core import Logger  # noqa
from .utils import create_log_context, request_id_var, set_request_id  # noqa

__all__ = ["request_id_var", "set_request_id", "create_log_context", "Logger"]
