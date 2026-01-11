from __future__ import annotations

import multiprocessing
import os
import sys

import uvicorn

try:
    import setproctitle

    SETPROCTITLE_AVAILABLE = True
except ImportError:
    SETPROCTITLE_AVAILABLE = False
    print("WARNING: setproctitle not installed. Process title will not be set.")

from config import Config

MAX_WORKERS = 64
DEFAULT_MAX_WORKERS_SMALL = 32
SHUTDOWN_TIMEOUT_DEFAULT = 20
KEEP_ALIVE_DEFAULT = 75


def calculate_workers(config_workers: int | str, development: bool) -> int:
    """Determine the optimal number of Uvicorn workers.

    Args:
    ----
        config_workers: The number of workers to use.
        development: Whether the application is in development mode.

    Returns:
    -------
        The number of workers to use.

    """
    if development:
        return 1

    cpu_count = multiprocessing.cpu_count()
    max_workers = MAX_WORKERS if cpu_count >= 32 else DEFAULT_MAX_WORKERS_SMALL
    auto_calculated = min(cpu_count * 2 + 1, max_workers)

    # Handle string input
    if isinstance(config_workers, str):
        if config_workers.strip().lower() == "auto":
            return auto_calculated
        if config_workers.isdigit():
            config_workers = int(config_workers)
        else:
            return auto_calculated

    # Handle non-integer or invalid input
    try:
        config_workers = int(config_workers)
    except (TypeError, ValueError):
        return auto_calculated

    if config_workers <= 0:
        return auto_calculated

    return min(config_workers, max_workers)


def set_process_title(
    config: Config, process_type: str = "main", worker_id: int = 0
) -> None:
    """Set the process title for system process lists.

    Args:
    ----
        config: The configuration.
        process_type: The type of process.
        worker_id: The ID of the worker.

    Returns:
    -------
        None

    """
    if not SETPROCTITLE_AVAILABLE:
        return

    title_format = config.get(
        "process_title_format",
        "fastapi-{app_title}-{environment}-{process_type}-{worker_id}",
    )

    app_title = config.get("app_title", "boilerplate").lower().replace(" ", "-")
    environment = config.get("environment", "development")

    process_title = title_format.format(
        app_title=app_title,
        environment=environment,
        process_type=process_type,
        worker_id=worker_id,
        pid=os.getpid(),
    )
    setproctitle.setproctitle(process_title)


def validate_critical_config(config: Config) -> None:
    """Validate critical application configuration.

    Args:
    ----
        config: The configuration.

    Returns:
    -------
        None

    """
    if not config.get("jwt_secret"):
        raise ValueError(
            "CRITICAL: JWT secret not configured. Set 'jwt_secret' in config."
        )

    host = config.get("app_host", "127.0.0.1")
    if host == "0.0.0.0":
        print(
            "WARNING: Binding to 0.0.0.0 exposes the app to the network. "
            "Consider using 127.0.0.1 for local development."
        )

    if not config.get("mongo_host"):
        print("WARNING: MongoDB host not configured; using defaults.")

    if not config.get("redis_host"):
        print("WARNING: Redis host not configured; using defaults.")


def main() -> None:
    """Main entry point to run the FastAPI app."""
    try:
        config = Config()
        validate_critical_config(config)
        set_process_title(config)

        workers = calculate_workers(config.get("app_workers"), config.get("app_debug"))

        uvicorn.run(
            "app:app",
            loop="uvloop",
            ws="wsproto",
            host=config.get("app_host", "127.0.0.1"),
            port=config.get("app_port", 8000),
            reload=config.get("app_reload", False),
            log_level=config.get("uvicorn_log_level", "critical"),
            workers=workers,
            lifespan=config.get("app_lifespan", "on"),
            timeout_keep_alive=config.get("app_timeout_keep_alive", KEEP_ALIVE_DEFAULT),
            timeout_graceful_shutdown=config.get(
                "app_timeout_graceful_shutdown", SHUTDOWN_TIMEOUT_DEFAULT
            ),
            access_log=config.get("log_uvicorn", False),
            ws_max_size=config.get("app_ws_max_size", int(1e8)),
            ws_ping_interval=config.get("app_ws_ping_interval", 25),
            ws_ping_timeout=config.get("app_ws_ping_timeout", 60),
            ws_per_message_deflate=config.get("app_ws_per_message_deflate", False),
            server_header=False,
            date_header=False,
        )

    except (ValueError, ImportError, OSError) as e:
        print(f"Failed to start application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
