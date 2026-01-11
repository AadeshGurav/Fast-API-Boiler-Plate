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

    # Create FastAPI app
    app = container.app()

except Exception as e:
    import traceback

    print(f"Failed to initialize application: {e}")
    print(traceback.format_exc())
    raise
