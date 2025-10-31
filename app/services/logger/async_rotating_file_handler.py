"""Async-friendly rotating file handler."""

from __future__ import annotations

import asyncio
import sys
from logging import Formatter, Handler, LogRecord
from logging.handlers import QueueListener, RotatingFileHandler
from pathlib import Path
from queue import Queue

from app.services.logger.utils import request_id_var


class AsyncRotatingFileHandler(Handler):
    """Async-friendly rotating file handler.

    Implementation details:
    - Uses a standard RotatingFileHandler internally for actual file writes and rotation.
    - Accepts records via .emit() and queues them in an asyncio.Queue when an event loop is present.
    - A background task drains the asyncio.Queue and calls the internal handler.emit in a thread via asyncio.to_thread,
      which ensures rotation and disk I/O happen on a thread (safe) while the producer is non-blocking.
    - If no asyncio loop is available (sync context), it can fall back to a threaded
      QueueListener by using start_sync_listener().
    """

    def __init__(
        self: AsyncRotatingFileHandler,
        file_path: str | Path,
        max_bytes: int = 10_485_760,
        backup_count: int = 5,
        formatter: Formatter | None = None,
    ) -> None:
        """Initialize AsyncRotatingFileHandler.

        Args:
        ----
            file_path: Path to the log file.
            max_bytes: Maximum size of the log file before rotation.
            backup_count: Number of backup files to retain.
            formatter: Formatter to use for the log file.

        """
        super().__init__()
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        # Internal RotatingFileHandler handles rotation and sync writes
        self._sync_handler = RotatingFileHandler(
            str(self.file_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        if formatter:
            self._sync_handler.setFormatter(formatter)
        self.setFormatter(formatter or self._sync_handler.formatter)

        # Async machinery
        self._queue: asyncio.Queue | None = None
        self._task: asyncio.Task | None = None
        self._stop_event: asyncio.Event | None = None

        # Sync fallback machinery
        self._thread_queue: Queue | None = None
        self._queue_listener: QueueListener | None = None

    def emit(self: AsyncRotatingFileHandler, record: LogRecord) -> None:
        """Called by logging framework. Queue record for eventual write.
        If async queue active, use it; otherwise, try to put in thread queue or write synchronously.

        Args:
        ----
            record: Log record to emit.

        """
        try:
            # attach request_id from contextvar if present and not present already
            if (
                not hasattr(record, "request_id")
                or getattr(record, "request_id") is None
            ):
                rid = request_id_var.get()
                if rid:
                    try:
                        setattr(record, "request_id", rid)
                    except Exception:  # noqa: BLE001
                        pass

            # Try async queue first
            if self._queue is not None:
                # Queue is asyncio.Queue; put_nowait may raise if full, but default unbounded is ok
                try:
                    self._queue.put_nowait(record)
                    return
                except Exception:  # noqa: BLE001
                    # fallthrough to thread queue
                    pass

            # If no async queue, fall back to thread queue (if present)
            if self._thread_queue is not None:
                try:
                    self._thread_queue.put_nowait(record)
                    return
                except Exception:  # noqa: BLE001
                    pass

            # Final fallback: synchronous write (rare)
            self._sync_handler.emit(record)
        except Exception as e:  # noqa: BLE001
            # Avoid raising inside logging.emit
            print(f"AsyncRotatingFileHandler.emit error: {e}", file=sys.stderr)

    # ---------- Async mode ----------
    def start_async(
        self: AsyncRotatingFileHandler, loop: asyncio.AbstractEventLoop | None = None
    ) -> None:
        """Start async background writer task. If already started, no-op.

        Args:
        ----
            loop: Event loop to use.

        """
        if self._task is not None:
            return
        loop = loop or asyncio.get_event_loop()
        self._queue = asyncio.Queue()
        self._stop_event = asyncio.Event()
        # create background task on provided loop
        self._task = loop.create_task(self._writer_loop())

    async def _writer_loop(self: AsyncRotatingFileHandler) -> None:
        """Async background writer: drains the asyncio.Queue and writes via internal sync handler in threads.

        Args:
        ----
            loop: Event loop to use.

        """
        assert self._queue is not None and self._stop_event is not None
        try:
            while not (self._stop_event.is_set() and self._queue.empty()):
                try:
                    record: LogRecord = await asyncio.wait_for(
                        self._queue.get(), timeout=0.1
                    )
                except asyncio.TimeoutError:
                    continue
                try:
                    # Use asyncio.to_thread to run the blocking emit (which may rotate files) in a thread
                    await asyncio.to_thread(self._sync_handler.emit, record)
                except Exception as e:  # noqa: BLE001
                    # if thread emit fails, write minimal fallback
                    print(
                        f"AsyncRotatingFileHandler writer emit failed: {e}",
                        file=sys.stderr,
                    )
                finally:
                    try:
                        self._queue.task_done()
                    except Exception:  # noqa: BLE001
                        pass
        except asyncio.CancelledError:
            # Task cancelled: flush remaining queue synchronously
            await self._drain_sync()
        except Exception as e:  # noqa: BLE001
            print(f"AsyncRotatingFileHandler writer loop error: {e}", file=sys.stderr)

    async def _drain_sync(self: AsyncRotatingFileHandler) -> None:
        """Drain any remaining records using threads to ensure flush/rotation on shutdown.

        Args:
        ----
            loop: Event loop to use.

        """
        if self._queue is None:
            return
        while not self._queue.empty():
            try:
                record: LogRecord = await self._queue.get()
                await asyncio.to_thread(self._sync_handler.emit, record)
                try:
                    self._queue.task_done()
                except Exception:  # noqa: BLE001
                    pass
            except Exception as e:  # noqa: BLE001
                print(f"AsyncRotatingFileHandler drain error: {e}", file=sys.stderr)

    async def stop_async(self: AsyncRotatingFileHandler) -> None:
        """Signal stop and await background task completion.

        Args:
        ----
            loop: Event loop to use.

        """
        if self._task is None or self._stop_event is None:
            return
        self._stop_event.set()
        try:
            await self._task
        except Exception:  # noqa: BLE001
            pass
        self._task = None
        self._stop_event = None
        self._queue = None

    # ---------- Sync fallback mode ----------
    def start_sync_listener(self: AsyncRotatingFileHandler) -> None:
        """Start a threaded QueueListener for environments without an event loop.

        Args:
        ----
            loop: Event loop to use.

        """
        if self._queue_listener is not None:
            return
        self._thread_queue = Queue(-1)
        self._queue_listener = QueueListener(self._thread_queue, self._sync_handler)
        self._queue_listener.start()

    def stop_sync_listener(self: AsyncRotatingFileHandler) -> None:
        """Stop the sync listener.

        Args:
        ----
            loop: Event loop to use.

        """
        if self._queue_listener is not None:
            try:
                self._queue_listener.stop()
            except Exception:  # noqa: BLE001
                pass
            self._queue_listener = None
            self._thread_queue = None

    # ---------- common helper ----------
    def close(self: AsyncRotatingFileHandler) -> None:
        """Close underlying handler.

        Args:
        ----
            loop: Event loop to use.

        """
        try:
            self._sync_handler.close()
        except Exception:  # noqa: BLE001
            pass
        super().close()


__all__ = ["AsyncRotatingFileHandler"]
