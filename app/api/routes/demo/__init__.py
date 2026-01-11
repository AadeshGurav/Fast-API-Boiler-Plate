"""Demo routes package for unified demo experience."""

from __future__ import annotations

from .files import files_router
from .files_play import files_play_router
from .health import router as health_router
from .library import library_router
from .sentry_example import router as sentry_router
from .unified_demo import demo_router

__all__ = [
    "demo_router",
    "files_router",
    "files_play_router",
    "health_router",
    "library_router",
    "sentry_router",
]
