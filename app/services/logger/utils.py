"""Utility functions for logger."""
from __future__ import annotations

import contextvars
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.logger.core import Logger


def create_log_context(**kwargs: Any) -> dict[str, Any]:
    """Create standardized log context dict.

    Args:
    ----
        **kwargs: Additional keyword arguments to log.

    Returns:
    -------
        Dictionary of log context.

    """
    return {k: v for k, v in kwargs.items() if v is not None}


request_id_var: contextvars.ContextVar["Logger", str | None] = contextvars.ContextVar(
    "request_id", default=None
)


def set_request_id(rid: str | None) -> None:
    """Set or clear current request id for logs (context-aware)."""
    request_id_var.set(rid)
