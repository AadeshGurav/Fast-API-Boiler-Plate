"""User repository interface for platform-agnostic user operations."""
from __future__ import annotations

from abc import abstractmethod

from app.core.interfaces.base_interface import BaseInterface


class UserRepositoryInterface(BaseInterface):
    """Interface for user repository operations."""

    @abstractmethod
    async def create_user(self, user_data: dict) -> dict:
        """Create a new user.

        Args:
            user_data: User data dictionary

        Returns:
            Created user data

        """
        pass

    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> dict | None:
        """Get user by ID.

        Args:
            user_id: User identifier

        Returns:
            User data or None if not found

        """
        pass

    @abstractmethod
    async def get_user_by_username(self, username: str) -> dict | None:
        """Get user by username.

        Args:
            username: Username

        Returns:
            User data or None if not found

        """
        pass

    @abstractmethod
    async def get_user_by_email(self, email: str) -> dict | None:
        """Get user by email.

        Args:
            email: Email address

        Returns:
            User data or None if not found

        """
        pass

    @abstractmethod
    async def update_user(self, user_id: str, updates: dict) -> bool:
        """Update user data.

        Args:
            user_id: User identifier
            updates: Update data dictionary

        Returns:
            True if updated successfully

        """
        pass

    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        """Delete user.

        Args:
            user_id: User identifier

        Returns:
            True if deleted successfully

        """
        pass

    @abstractmethod
    async def assign_roles(self, user_id: str, roles: list[str]) -> bool:
        """Assign roles to user.

        Args:
            user_id: User identifier
            roles: List of role IDs

        Returns:
            True if assigned successfully

        """
        pass

    @abstractmethod
    async def assign_groups(self, user_id: str, groups: list[str]) -> bool:
        """Assign groups to user.

        Args:
            user_id: User identifier
            groups: List of group IDs

        Returns:
            True if assigned successfully

        """
        pass


__all__ = ["UserRepositoryInterface"]
