"""Demo routes package for unified demo experience."""
from __future__ import annotations

from .health import router as health_router
from .sentry_example import router as sentry_router
from .unified_demo import demo_router

__all__ = ["demo_router", "health_router", "sentry_router"]
