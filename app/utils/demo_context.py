"""Unified user context helper for demo pages.

Provides consistent user object format across all demo routes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Request

from app import container
from app.services.data import DataService
from app.utils.permissions import get_current_user

if TYPE_CHECKING:
    pass

_USER_CACHE: dict[str, dict[str, Any]] = {}


async def get_demo_user_context(request: Request) -> dict[str, Any] | None:
    """Get unified user context for demo templates.

    Provides consistent user object format across all demo routes.
    Includes user permissions, roles, and metadata.

    Args:
    ----
        request: FastAPI request object

    Returns:
    -------
        User dictionary with standardized format or None if not authenticated.
        Format: {
            "id": str,
            "username": str,
            "email": str,
            "role": str,
            "roles": list[str],
            "groups": list[str],
            "status": str,
            "permissions": list[str],
            "avatar_url": str | None,
            "created_at": str | None,
            "last_login": str | None,
        }

    """
    try:
        token_payload = await get_current_user(request)
        if not token_payload:
            return None

        user_id = (
            token_payload.user_id
            if hasattr(token_payload, "user_id")
            else token_payload.get("user_id")
        )

        if not user_id:
            return None

        # Check cache first
        cache_key = f"user_{user_id}"
        if cache_key in _USER_CACHE:
            return _USER_CACHE[cache_key]

        # Get user data from database
        data_service: DataService = container.data_service()
        user_data = await data_service.users.get_user_by_id(user_id)

        if not user_data:
            return None

        # Extract permissions from token payload
        permissions = []
        if hasattr(token_payload, "permissions"):
            permissions = token_payload.permissions
        elif isinstance(token_payload, dict):
            permissions = token_payload.get("permissions", [])

        # Format dates with validation
        from datetime import datetime

        created_at = None
        if user_data.get("created_at"):
            created_at_obj = user_data["created_at"]
            if hasattr(created_at_obj, "strftime"):
                # Validate date is not in the future
                if created_at_obj > datetime.now():
                    created_at_obj = datetime.now()
                created_at = created_at_obj.strftime("%Y-%m-%d")
            else:
                created_at = str(created_at_obj)

        last_login = None
        if user_data.get("last_login"):
            last_login_obj = user_data["last_login"]
            if hasattr(last_login_obj, "strftime"):
                # Validate date is not in the future
                if last_login_obj > datetime.now():
                    last_login_obj = datetime.now()
                last_login = last_login_obj.strftime("%Y-%m-%d %H:%M:%S")
            else:
                last_login = str(last_login_obj)

        # Determine primary role - prioritize admin if present
        roles = user_data.get("roles", [])
        if not roles:
            roles = [user_data.get("role", "user")]
        if isinstance(roles, str):
            roles = [roles]

        # Prioritize admin role if it exists
        primary_role = "user"
        if "admin" in roles:
            primary_role = "admin"
        elif "manager" in roles:
            primary_role = "manager"
        elif roles:
            primary_role = roles[0]

        # Build unified user context
        user_context = {
            "id": user_data.get("id"),
            "username": user_data.get("username", ""),
            "email": user_data.get("email", ""),
            "role": primary_role,
            "roles": roles,
            "groups": user_data.get("groups", []),
            "status": user_data.get("status", "active"),
            "permissions": permissions,
            "avatar_url": None,
            "created_at": created_at,
            "last_login": last_login,
        }

        # Cache user context
        _USER_CACHE[cache_key] = user_context

        return user_context

    except HTTPException:
        return None
    except (ValueError, KeyError, AttributeError, TypeError):
        return None
    except Exception:
        return None


def clear_user_cache(user_id: str | None = None) -> None:
    """Clear user context cache.

    Args:
    ----
        user_id: Specific user ID to clear, or None to clear all

    """
    global _USER_CACHE

    if user_id:
        cache_key = f"user_{user_id}"
        _USER_CACHE.pop(cache_key, None)
    else:
        _USER_CACHE.clear()
