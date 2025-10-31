from __future__ import annotations
from abc import abstractmethod
from collections.abc import Callable
from typing import Any

from .base_interface import BaseInterface


class AuthServiceInterface(BaseInterface):
    """Authentication Service."""

    @abstractmethod
    def create_tokens(
        self, data: dict[str, Any], user_role: str = "user"
    ) -> tuple[str, str]:
        """Create both access and refresh tokens with role information."""
        pass

    @abstractmethod
    def create_access_token(self, data: dict[str, Any]) -> str:
        """Create a JWT access token."""
        pass

    @abstractmethod
    def create_refresh_token(self, data: dict[str, Any]) -> str:
        """Create a JWT refresh token."""
        pass

    @abstractmethod
    def decode_token(
        self, token: str, verify_type: str | None = None
    ) -> dict[str, Any]:
        """Decode and validate a JWT token."""
        pass

    @abstractmethod
    async def get_current_user(self, access_token: str = None) -> dict[str, Any]:
        """Get the current user from the access token."""
        pass

    @abstractmethod
    async def is_admin(self, current_user: dict[str, Any]) -> bool:
        """Check if the current user is an admin."""
        pass

    @abstractmethod
    def admin_required(self, func: Callable) -> Callable:
        """Decorator to require admin role for a route."""
        pass

    @abstractmethod
    def login(self, user: Any) -> Any:
        """Log user login event.

        Args:
            user: The user to log in.

        """
        pass


__all__ = ["AuthServiceInterface"]
