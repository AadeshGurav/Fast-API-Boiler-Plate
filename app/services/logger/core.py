"""Core logger class."""

from __future__ import annotations

import asyncio
import logging
import random
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dependency_injector.wiring import inject

from app.services.logger.async_rotating_file_handler import AsyncRotatingFileHandler
from app.services.logger.colored_formatter import ColoredFormatter
from app.services.logger.level_filter import LevelFilter
from app.services.logger.safe_json_formatter import SafeJsonFormatter

if TYPE_CHECKING:
    from config import Config


class Logger:
    """A robust, singleton logger supporting both async and sync contexts with structured and colored logging.

    Features:
    -------------
    1. **Singleton**: Ensures only one logger instance per application.
    2. **Structured Logging**: Outputs NDJSON (newline-delimited JSON) to log files with standardized fields:
       - timestamp, hostname, service, level, logger_name
       - request_id (automatically propagated using contextvars)
       - extra fields provided via `extra` argument
    3. **Colored Console Output**: Human-readable, color-coded logs in the terminal.
    4. **Level-specific Rotating Files**: Writes logs to separate files per level
       (DEBUG, INFO, ERROR) with rotation support.
    5. **Async-friendly File Logging**:
       - Non-blocking log writes using `asyncio.Queue`.
       - Background tasks drain the queue and write logs using `RotatingFileHandler` in a thread-safe manner.
    6. **Sync Fallback**: Threaded `QueueListener` for CLI or sync-only contexts.
    7. **Context-aware Request IDs**: Supports per-request IDs that flow through async and sync calls.
    8. **Sampling**: Optional sampling for lower levels to reduce log volume (`sample_rate`).

    Usage:
    -------------
    ```python
    from logger_module import Logger, set_request_id

    logger = Logger()

    # Set a request ID for tracing logs
    set_request_id("req-1234")

    # Log messages
    logger.debug("Debug message")
    logger.info("Info message", extra={"user": "alice"})
    logger.error("Error occurred!", exc_info=True)

    # Async app startup
    await logger.enable_async()  # start async background writers

    # Shutdown during app exit
    await logger.shutdown()       # async apps
    logger.shutdown_sync()        # sync apps or fallback
    ```

    Initialization Parameters:
    ----------------------------
    - `name`: Logger name (default: app title from DI container or "fastapi-app").
    - `log_path`: Directory path for log files (default: "logs").
    - `level`: Minimum log level (DEBUG, INFO, etc.).
    - `max_bytes`: Maximum size of a log file before rotation.
    - `backup_count`: Number of rotated files to retain.
    - `sample_rate`: Probability [0.0-1.0] of logging lower-level messages (DEBUG/INFO).

    Public Methods:
    ----------------
    - `debug()`, `info()`, `warning()`, `error()`, `critical()`, `exception()`
      → Convenience logging methods.
    - `enable_async(loop=None)` → Start async background log writers.
    - `enable_sync_fallback()` → Use thread-based logging for sync contexts.
    - `shutdown()` → Gracefully stop async writers (async context).
    - `shutdown_sync()` → Stop sync listeners and attempt to flush logs (sync context).

    Notes
    -----
    - Designed for FastAPI or other async Python applications but works in sync scripts.
    - Request IDs automatically propagate via `contextvars`, no need to manually pass them to each log call.
    - JSON logs are NDJSON formatted for easy ingestion into log management systems (e.g., ELK stack, Datadog).

    """

    _instance: Logger | None = None
    _initialized: bool = False

    def __new__(
        cls: type[Logger], *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Logger:
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
            cls._instance: cls = super().__new__(cls)
        return cls._instance

    @inject
    def __init__(
        self: Logger,
        config: Config,
    ) -> None:
        """Initialize Logger.

        Args:
        ----
            config: Configuration object.

        """
        if self._initialized:
            return

        # setup instance variables
        self.config: Config = config
        self.name: str = self.config.get("app_title", "fastapi-app")
        self.log_path: Path = Path(self.config.get("logs_path", "logs"))
        self.level: int = self.config.get("log_level", logging.INFO)
        self.max_bytes: int = self.config.get("log_max_bytes", 10_485_760)
        self.backup_count: int = self.config.get("log_backup_count", 5)
        self.sample_rate: float = self.config.get("log_sample_rate", 1.0)
        self.console_formatter_text: str = self.config.get(
            "log_console_formatter_text",
            "%(levelname)s | %(asctime)s | %(name)s:%(lineno)d | %(message)s",
        )
        self.file_formatter_text: str = self.config.get(
            "log_file_formatter_text",
            "%(message)s",
        )

        # set logging level
        if isinstance(self.level, str):
            self.level = logging._levelToName.get(
                logging._nameToLevel.get(self.level, logging.INFO)
            )
        elif isinstance(self.level, int):
            self.level = logging._levelToName.get(self.level, logging.INFO)
        else:
            # Considering some oversmart admin changes the value to a bool or float in config.
            self.level = logging.INFO

        if not 0.0 <= self.sample_rate <= 1.0:
            self.sample_rate = 1.0
            print(
                f"Warning: Invalid sample_rate {self.sample_rate}, using 1.0",
                file=sys.stderr,
            )

        # prepare logger
        self.logger: logging.Logger = logging.getLogger(self.name)
        self.logger.setLevel(self.level)
        self.logger.propagate = False

        # keep references to async handlers for shutdown
        self._async_handlers: list[AsyncRotatingFileHandler] = []
        # track whether we started async tasks
        self._async_mode_enabled: bool = False
        self._sync_fallback_enabled: bool = False

        # setup handlers
        self._setup_handlers()

        self._initialized = True
        self.logger.info("Logger Service Initialized")

    def _setup_handlers(self: Logger) -> None:
        """Create console and file handlers per level, but do not start background tasks automatically."""
        # Ensure directory exists
        self.log_path.mkdir(parents=True, exist_ok=True)  # type: ignore

        # Formatters
        file_formatter: SafeJsonFormatter = SafeJsonFormatter(self.file_formatter_text)
        console_formatter: ColoredFormatter = ColoredFormatter(
            self.console_formatter_text
        )

        # Console handler (human readable)
        console_handler: logging.StreamHandler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(self.level)
        # Always attach console (no duplication check here; user may attach multiple times in different runs)
        self.logger.addHandler(console_handler)

        # Rotating file handlers per level
        level_files: list[tuple[int, Path]] = [
            (logging.DEBUG, self.log_path / "debug_log.jsonl"),
            (logging.INFO, self.log_path / "info_log.jsonl"),
            (logging.WARNING, self.log_path / "warning_log.jsonl"),
            (logging.ERROR, self.log_path / "error_log.jsonl"),
            (logging.CRITICAL, self.log_path / "critical_log.jsonl"),
        ]

        for lvl, path in level_files:
            handler: AsyncRotatingFileHandler = AsyncRotatingFileHandler(
                path,
                max_bytes=self.max_bytes,
                backup_count=self.backup_count,
                formatter=file_formatter,
            )
            handler.setLevel(lvl)
            handler.addFilter(LevelFilter(lvl))
            self.logger.addHandler(handler)
            self._async_handlers.append(handler)

        # Try to auto-start async mode if loop available
        try:
            loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()

            if loop.is_running():
                # start async writer tasks
                for h in self._async_handlers:
                    h.start_async(loop=loop)
                self._async_mode_enabled = True
            else:
                # If loop exists but not running, we do not start async by default: leave caller to call enable_async()
                self._async_mode_enabled = False

        except RuntimeError:
            # No event loop in this thread; enable thread-based fallback listener
            for h in self._async_handlers:
                h.start_sync_listener()
            self._sync_fallback_enabled = True

    def enable_async(
        self: Logger, loop: asyncio.AbstractEventLoop | None = None
    ) -> None:
        """Explicitly enable async writer tasks. Call this from your app startup (when event loop is running).

        Args:
        ----
            loop: Event loop to use.

        """
        if self._async_mode_enabled:
            return

        loop: asyncio.AbstractEventLoop = loop or asyncio.get_event_loop()

        if not loop.is_running():
            raise RuntimeError(
                "Event loop is not running; call enable_async from within running loop (e.g., app startup)."
            )

        # stop sync listeners if any
        if self._sync_fallback_enabled:
            for h in self._async_handlers:
                h.stop_sync_listener()
            self._sync_fallback_enabled = False

        for h in self._async_handlers:
            h.start_async(loop=loop)
        self._async_mode_enabled = True

    def enable_sync_fallback(self: Logger) -> None:
        """Enable thread-based listener fallback (useful for CLI or sync contexts)."""
        if self._sync_fallback_enabled:
            return

        # stop any async tasks first
        if self._async_mode_enabled:
            # we won't await tasks here; call shutdown_async() for clean shutdown if needed
            for h in self._async_handlers:
                # if tasks are running, they will be stopped in shutdown
                pass
            self._async_mode_enabled = False

        for h in self._async_handlers:
            h.start_sync_listener()
        self._sync_fallback_enabled = True

    def _should_log(self: Logger, level: int) -> bool:
        """Sampling logic: always log errors and above; sample below that based on sample_rate.

        Args:
        ----
            level: Level to check.

        Returns:
        -------
            True if the level should be logged, False otherwise.

        """
        if level >= logging.ERROR:
            return True
        if self.sample_rate >= 1.0:
            return True

        return random.random() < self.sample_rate

    def _log(
        self: Logger,
        level: int,
        msg: str,
        *args: dict[str, Any],
        exc_info: Any = None,
        extra: dict[str, Any] | None = None,
        **kwargs: dict[str, Any],
    ) -> None:
        """Internal logging wrapper used by convenience methods.

        Args:
        ----
            level: Level to log.
            msg: Message to log.
            *args: Additional arguments to log.
            exc_info: Exception information to log.
            extra: Extra fields to log.
            **kwargs: Additional keyword arguments to log.

        """
        if not self._should_log(level):
            return

        log_extra: dict[str, Any] = {}
        if extra:
            log_extra["extra_fields"] = extra

        try:
            # stacklevel=2 skips: debug/info/etc → _log → logger.log
            # This makes logging.Logger.log() look 2 frames up to find the actual caller
            self.logger.log(
                level,
                msg,
                *args,
                exc_info=exc_info,
                extra=log_extra,
                stacklevel=4,  # Skip wrapper frames to get actual caller
                **kwargs,
            )
        except Exception as e:  # noqa: BLE001
            # avoid raising in logging path
            print(f"Logging failed: {e}", file=sys.stderr)

    # Public convenience methods (preserve names)
    def debug(
        self: Logger, msg: str, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> None:
        """Log a debug message.

        Args:
        ----
            msg: Message to log.
            *args: Additional arguments to log.
            **kwargs: Additional keyword arguments to log.

        """
        self._log(logging.DEBUG, msg, *args, **kwargs)

    def info(
        self: Logger, msg: str, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> None:
        """Log an info message.

        Args:
        ----
            msg: Message to log.
            *args: Additional arguments to log.
            **kwargs: Additional keyword arguments to log.

        """
        self._log(logging.INFO, msg, *args, **kwargs)

    def warning(
        self: Logger, msg: str, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> None:
        """Log a warning message.

        Args:
        ----
            msg: Message to log.
            *args: Additional arguments to log.
            **kwargs: Additional keyword arguments to log.

        """
        self._log(logging.WARNING, msg, *args, **kwargs)

    def error(
        self: Logger, msg: str, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> None:
        """Log an error message.

        Args:
        ----
            msg: Message to log.
            *args: Additional arguments to log.
            **kwargs: Additional keyword arguments to log.

        """
        self._log(logging.ERROR, msg, *args, **kwargs)

    def critical(
        self: Logger, msg: str, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> None:
        """Log a critical message.

        Args:
        ----
            msg: Message to log.
            *args: Additional arguments to log.
            **kwargs: Additional keyword arguments to log.

        """
        self._log(logging.CRITICAL, msg, *args, **kwargs)

    def exception(
        self: Logger,
        msg: str,
        *args: dict[str, Any],
        exc_info: Any = True,
        **kwargs: dict[str, Any],
    ) -> None:
        """Log an exception message.

        Args:
        ----
            msg: Message to log.
            *args: Additional arguments to log.
            exc_info: Exception information to log.
            **kwargs: Additional keyword arguments to log.

        """
        self._log(logging.ERROR, msg, *args, exc_info=exc_info, **kwargs)

    # Shutdown helpers
    async def shutdown(self: Logger) -> None:
        """Gracefully stop async writers and flush logs.
        Call this from async shutdown hooks (e.g., FastAPI shutdown event).
        """
        # If in async mode, stop async handlers
        if self._async_mode_enabled:
            await asyncio.gather(
                *(h.stop_async() for h in self._async_handlers), return_exceptions=True
            )
            self._async_mode_enabled = False

        # Stop any sync listeners
        if self._sync_fallback_enabled:
            for h in self._async_handlers:
                h.stop_sync_listener()
            self._sync_fallback_enabled = False

        # close underlying handlers
        for h in self._async_handlers:
            try:
                h.close()
            except Exception:  # noqa: BLE001
                pass

    def shutdown_sync(self: Logger) -> None:
        """Synchronous shutdown fallback. For sync apps, call this on process exit.
        It will stop thread-based queue listeners (if any) and attempt to flush remaining records.
        """
        # Stop any sync listeners
        if self._sync_fallback_enabled:
            for h in self._async_handlers:
                h.stop_sync_listener()
            self._sync_fallback_enabled = False

        # If async tasks were enabled but we are in sync context, attempt to stop them
        # synchronously by cancelling/waiting.
        if self._async_mode_enabled:
            # In most apps, you should call shutdown() from async context; here we attempt a best-effort flush.
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except Exception:  # noqa: BLE001
                loop = None

            if loop and loop.is_running():
                # schedule shutdown coroutine and wait: (should be rarely used)
                fut = asyncio.run_coroutine_threadsafe(self.shutdown(), loop)
                try:
                    fut.result(timeout=5.0)
                except Exception:  # noqa: BLE001
                    pass
            else:
                # no event loop to await async writers; attempt to stop via thread-based fallback:
                for h in self._async_handlers:
                    h.stop_sync_listener()

        # close underlying handlers
        for h in self._async_handlers:
            try:
                h.close()
            except Exception:  # noqa: BLE001
                pass


__all__ = ["Logger"]
