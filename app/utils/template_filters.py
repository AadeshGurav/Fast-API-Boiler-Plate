"""Jinja2 template filters for safe data serialization."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def safe_user_json(user_dict: dict[str, Any] | None) -> dict[str, Any] | None:
    """Recursively convert datetime objects to ISO format strings for JSON serialization.

    Args:
    ----
        user_dict: User dictionary that may contain datetime objects

    Returns:
    -------
        Dictionary with all datetime objects converted to ISO format strings

    """
    if user_dict is None:
        return None

    def convert_datetime(obj: Any) -> Any:  # noqa: ANN001, ANN401
        """Recursively convert datetime objects to ISO format strings."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {key: convert_datetime(value) for key, value in obj.items()}
        if isinstance(obj, list):
            return [convert_datetime(item) for item in obj]
        return obj

    return convert_datetime(user_dict)
