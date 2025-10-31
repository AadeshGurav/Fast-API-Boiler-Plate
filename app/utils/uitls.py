"""Lifecycle management utilities for FastAPI applications."""
from __future__ import annotations

import asyncio
import hashlib
import secrets
import signal
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from types import FrameType, TracebackType

from fastapi import FastAPI, Request
from user_agents import parse

from app.models.session import DeviceInfo
from app.services.logger import Logger

_shutdown_event: asyncio.Event | None = None


def get_shutdown_event() -> asyncio.Event:
    """Return the global asyncio event used for graceful shutdown.

    Returns
    -------
        asyncio.Event: The global asyncio event used for graceful shutdown.

    """
    global _shutdown_event
    if _shutdown_event is None:
        _shutdown_event = asyncio.Event()
    return _shutdown_event


async def wait_for_shutdown(timeout: float = 30.0) -> None:
    """Block until a shutdown signal is received or timeout elapses.

    Args:
    ----
        timeout: The timeout in seconds.

    Returns:
    -------
        None

    """
    event = get_shutdown_event()
    try:
        await asyncio.wait_for(event.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage FastAPI application startup and shutdown lifecycle.

    Args:
    ----
        app: The FastAPI application.

    Returns:
    -------
        AsyncGenerator[None, None]: The lifespan generator.

    """
    logger: Logger | None = getattr(app.state, "logger", None)
    if logger:
        logger.info("Starting application lifecycle...")
        # Enable async mode for non-blocking log writes
        try:
            logger.enable_async()
            logger.info("Logger async mode enabled")
        except Exception as e:
            logger.warning(f"Failed to enable logger async mode: {e}")

    try:
        from app import _initialize_app, container

        # Initialize container if not already done
        if container is None:
            _initialize_app()

        data_service = getattr(app.state, "data_service", None)

        # Connect data layer
        if data_service:
            await data_service.connect()
            if logger:
                logger.info("DataService connections established")

        # Initialize RBAC system
        try:
            rbac_service = container.rbac_service()
            await rbac_service.load_rbac_config()

            if logger:
                logger.info("RBAC system initialized successfully")

            # Schedule periodic RBAC refresh
            async def periodic_rbac_refresh():
                """Periodic RBAC configuration refresh task."""
                while True:
                    try:
                        await asyncio.sleep(300)  # 5 minutes
                        await rbac_service.refresh_rbac_config()
                        if logger:
                            logger.debug("RBAC configuration refreshed")
                    except Exception as e:
                        if logger:
                            logger.error(f"RBAC refresh failed: {e}")
                        await asyncio.sleep(60)  # Wait 1 minute before retry

            # Start periodic refresh task
            refresh_task = asyncio.create_task(
                periodic_rbac_refresh(), name="rbac_refresh"
            )
            app.state.rbac_refresh_task = refresh_task

            if logger:
                logger.info("RBAC periodic refresh scheduled: every 5 minutes")

        except Exception as e:
            if logger:
                logger.error(f"RBAC initialization failed: {e}")
            # Don't fail startup if RBAC fails, but log the error

        # Initialize OAuth providers if enabled
        try:
            oauth_service = container.oauth_service()
            if oauth_service.oauth_enabled:
                providers = list(oauth_service.providers.keys())
                if logger:
                    logger.info(f"OAuth providers initialized: {providers}")
            else:
                if logger:
                    logger.info("OAuth providers disabled")
        except Exception as e:
            if logger:
                logger.error(f"OAuth initialization failed: {e}")

        if logger:
            logger.info("Application startup completed successfully")
            logger.info(
                f"http://{app.state.config.get('app_host', '127.0.0.1')}:{app.state.config.get('app_port', 8000)}"
            )

    except Exception as exc:
        if logger:
            logger.exception("Application startup failed", exc_info=exc)
        raise

    # Yield control to the running app
    yield

    # --- Shutdown Phase ---
    if logger:
        logger.info("Beginning graceful shutdown...")

    try:
        data_service = getattr(app.state, "data_service", None)
        metrics_service = getattr(app.state, "metrics_service", None)
        tracing_service = getattr(app.state, "tracing_service", None)
        shutdown_timeout = 30.0

        # Wait for in-flight requests if metrics available
        if metrics_service:
            start_time = asyncio.get_event_loop().time()
            while True:
                active_requests = 0
                try:
                    for metric in metrics_service.active_requests._metrics.values():
                        active_requests += metric._value.get()
                except Exception:
                    break

                if active_requests == 0:
                    break

                if asyncio.get_event_loop().time() - start_time > shutdown_timeout:
                    if logger:
                        logger.warning(
                            "Shutdown timeout reached with %d active requests",
                            active_requests,
                        )
                    break

                await asyncio.sleep(0.1)

        # Close bulkheads or pools if available
        bulkhead_manager = getattr(app.state, "bulkhead_manager", None)
        if bulkhead_manager:
            bulkhead_manager.shutdown_all()
            if logger:
                logger.info("Bulkheads shut down")

        # Close tracing resources if any
        if tracing_service and hasattr(tracing_service, "close"):
            try:
                tracing_service.close()
                if logger:
                    logger.info("Tracing resources closed")
            except Exception as exc:  # noqa: BLE001
                if logger:
                    logger.error("Error closing tracing resources: %s", exc)

        # Flush async logger if implemented
        if logger and hasattr(logger, "shutdown"):
            try:
                await logger.shutdown()
                logger.info("Logger shutdown complete")
            except Exception as e:
                print(f"Logger shutdown error: {e}", file=sys.stderr)

        # Close database and cache
        if data_service:
            await data_service.close()
            if logger:
                logger.info("Database connections closed")

            cache_service = getattr(data_service, "cache_service", None)
            if cache_service and hasattr(cache_service, "close"):
                await cache_service.close()
                if logger:
                    logger.info("Cache connections closed")

        # Cancel RBAC refresh task
        rbac_refresh_task = getattr(app.state, "rbac_refresh_task", None)
        if rbac_refresh_task:
            rbac_refresh_task.cancel()
            try:
                await rbac_refresh_task
            except asyncio.CancelledError:
                pass
            if logger:
                logger.info("RBAC refresh task cancelled")

        # Execute any app cleanup tasks
        cleanup_tasks = getattr(app.state, "cleanup_tasks", [])
        for task in cleanup_tasks:
            try:
                await task()
            except Exception as exc:
                if logger:
                    logger.error("Error during cleanup task: %s", exc)

        if logger:
            logger.info("Graceful shutdown complete")

    except Exception as exc:
        if logger:
            logger.exception("Error during shutdown", exc_info=exc)
    finally:
        # Clear app state to free resources
        try:
            for attr in list(app.state.__dict__.keys()):
                delattr(app.state, attr)
        except Exception:
            pass


def generate_session_id() -> str:
    """Generate a secure URL-safe session identifier.

    Returns
    -------
        str: The generated session identifier.

    """
    return secrets.token_urlsafe(32)


def get_client_ip(request) -> str:
    """Return the client's IP address from headers or connection info."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    if request.client:
        return request.client.host

    return "unknown"


def parse_bearer_token(authorization: str | None) -> str | None:
    """Extract a Bearer token from the Authorization header if valid."""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


class GracefulShutdown:
    """Context manager for handling graceful shutdown in background tasks."""

    def __init__(self, logger: Logger | None = None) -> None:
        """Initialize the GracefulShutdown context manager.

        Args:
        ----
            logger: The logger.

        """
        self.logger = logger
        self.tasks: list[asyncio.Task] = []
        self._shutdown_event = get_shutdown_event()

    def create_task(self, coro, name: str | None = None) -> asyncio.Task:
        """Register a background task that should stop on shutdown.

        Args:
        ----
            coro: The coroutine to register.
            name: The name of the task.

        Returns:
        -------
            asyncio.Task: The registered task.

        """
        task = asyncio.create_task(coro, name=name)
        self.tasks.append(task)
        return task

    async def wait_for_shutdown(self) -> None:
        """Block until a shutdown signal is received."""
        await self._shutdown_event.wait()

    async def shutdown(self, timeout: float = 10.0) -> None:
        """Cancel all background tasks and wait for their completion.

        Args:
        ----
            timeout: The timeout in seconds.

        Returns:
        -------
            None

        """
        if not self.tasks:
            return

        if self.logger:
            self.logger.info("Cancelling %d background tasks...", len(self.tasks))

        for task in self.tasks:
            task.cancel()

        try:
            await asyncio.wait_for(
                asyncio.gather(*self.tasks, return_exceptions=True), timeout=timeout
            )
        except asyncio.TimeoutError:
            if self.logger:
                self.logger.warning(
                    "Timeout waiting for %d tasks to complete", len(self.tasks)
                )

    async def __aenter__(self) -> "GracefulShutdown":
        """Enter the context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the context manager."""
        """Exit the context manager.

        Args:
            exc_type: The exception type.
            exc_val: The exception value.
            exc_tb: The exception traceback.

        Returns:
            None

        """
        await self.shutdown()


def handle_shutdown_signal(signum: int, frame: FrameType) -> None:
    """Handle termination signals and trigger application shutdown.

    Args:
    ----
        signum: The signal number.
        frame: The frame.

    Returns:
    -------
        None

    """
    shutdown_event = get_shutdown_event()
    shutdown_event.set()

    try:
        import logging

        logger = logging.getLogger(__name__)
        logger.info(
            "Received signal %s, initiating shutdown...",
            signal.Signals(signum).name,
        )
    except Exception:
        print(f"Received signal {signum}, initiating shutdown...")


def __generate_device_fingerprint(ip: str, user_agent: str, extra: str = "") -> str:
    """Generate a device fingerprint using a hash.

    Args:
    ----
        ip: The IP address.
        user_agent: The user agent.
        extra: Extra information to include in the fingerprint.

    Returns:
    -------
        The fingerprint.

    """
    # Combine values
    base_string = f"{ip}|{user_agent[:200]}|{extra}"

    # Use SHA256 hash for uniqueness
    fingerprint_hash = hashlib.sha256(base_string.encode()).hexdigest()

    # Keep first 12 chars for debugging reference
    debug_fingerprint = f"{fingerprint_hash[:12]}:{base_string[:50]}"

    return debug_fingerprint


def extract_device_info(request: Request) -> DeviceInfo:
    """Extract device information from request.

    Args:
    ----
        request: The request to extract device info from.

    Returns:
    -------
        Device information.

    """
    user_agent = request.headers.get("user-agent", "")
    ip_address = request.headers.get(
        "x-forwarded-for", request.client.host if request.client else "unknown"
    )
    language = request.headers.get("accept-language", None)

    # Parse user agent
    ua = parse(user_agent)
    platform = ua.os.family
    os_version = ua.os.version_string
    browser = ua.browser.family
    browser_version = ua.browser.version_string
    device_type = "Mobile" if ua.is_mobile else "Tablet" if ua.is_tablet else "PC"
    is_bot = ua.is_bot

    # Generate fingerprint
    extra_info = language or ""
    fingerprint = __generate_device_fingerprint(ip_address, user_agent, extra_info)

    # Optional: add geo-location lookup here

    return DeviceInfo(
        user_agent=user_agent,
        ip_address=ip_address,
        fingerprint=fingerprint,
        platform=platform,
        os_version=os_version,
        browser=browser,
        browser_version=browser_version,
        device_type=device_type,
        language=language,
        is_bot=is_bot,
        geo_location=None,  # placeholder for future
    )


# Register OS signal handlers
signal.signal(signal.SIGTERM, handle_shutdown_signal)
signal.signal(signal.SIGINT, handle_shutdown_signal)
signal.signal(signal.SIGINT, handle_shutdown_signal)
