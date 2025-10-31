"""The main module for the application."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI

if TYPE_CHECKING:
    from app.core.container import Container
    from app.services.auth import AuthService
    from app.services.data_service import DataService
    from app.services.error.error_service import ErrorService
    from app.services.logger import Logger
    from app.services.session import SessionService
    from config import Config

# Module-level variables
container: Container | None = None
config: Config | None = None
logger: Logger | None = None
auth_service: AuthService | None = None
session_service: SessionService | None = None
data_service: DataService | None = None
error_service: ErrorService | None = None
app: FastAPI | None = None


def _initialize_app() -> None:
    """Initialize the application components automatically."""
    global container
    global config
    global logger
    global auth_service
    global session_service
    global data_service
    global error_service
    global app

    try:
        from app.core.container import Container as _Container

        # Create and initialize container
        container = _Container()
        container.wire(modules=["config", "app.services.logger"])
        container.init_resources()

        # Get services from container
        config = container.config()
        logger = container.logger()
        auth_service = container.auth_service()
        session_service = container.session_service()
        data_service = container.data_service()
        error_service = container.error_service()

        # Create FastAPI app
        app = container.app()

    except Exception as e:
        import traceback

        print(f"Failed to initialize application: {e}")
        print(traceback.format_exc())
        raise


# Initialize app automatically when module is imported
_initialize_app()
