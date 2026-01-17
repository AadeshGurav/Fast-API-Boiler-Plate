"""The main module for the application."""

from __future__ import annotations

from fastapi import FastAPI

from app.core.container import Container

container: Container | None = None
app: FastAPI | None = None

try:
    # Create and initialize container
    container = Container()

    container.init_resources()

    # Discover and register services/classes (includes library_manager, etc.)
    # Access class_store and trigger discovery directly
    class_store_instance = container.class_store()
    # Set container reference for service access
    class_store_instance._container = container
    class_store_instance.discover_services(
        ["app.services", "app.api", "app.classes"]
    )

    # Create FastAPI app
    app = container.app()

except Exception as e:
    import traceback

    print(f"Failed to initialize application: {e}")
    print(traceback.format_exc())
    raise
