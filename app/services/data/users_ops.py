from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from .policies import CachePolicy

if TYPE_CHECKING:
    from .data_service import DataService


class UsersOps:
    """User-related data operations built on core CRUD."""

    def __init__(self: UsersOps, service: DataService) -> None:
        """Initialize UsersOps.

        Args:
        ----
            service: DataService instance.

        """
        self.service = service
        self.collection = "users"

    async def create_user(self: UsersOps, user_data: dict[str, Any]) -> str:
        """Create a new user.

        Args:
        ----
            user_data: User data dictionary.

        Returns:
        -------
            User ID.

        """
        user_id = user_data.get("id") or str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        user_data |= {"id": user_id, "created_at": now, "updated_at": now}
        await self.service.set(
            self.collection,
            {"id": user_id},
            user_data,
            policy=CachePolicy.DB_ONLY,
        )
        return user_id

    async def get_user_by_id(self: UsersOps, user_id: str) -> dict | None:
        """Get user by ID.

        Args:
        ----
            user_id: User ID.

        Returns:
        -------
            User dictionary or None if not found.

        """
        return await self.service.get(
            self.collection, {"id": user_id}, policy=CachePolicy.AUTO
        )

    async def get_user_by_username(self: UsersOps, username: str) -> dict | None:
        """Get user by username.

        Args:
        ----
            username: Username.

        Returns:
        -------
            User dictionary or None if not found.

        """
        return await self.service.get(
            self.collection, {"username": username}, policy=CachePolicy.AUTO
        )

    async def get_user_by_email(self: UsersOps, email: str) -> dict | None:
        """Get user by email.

        Args:
        ----
            email: Email address.

        Returns:
        -------
            User dictionary or None if not found.

        """
        return await self.service.get(
            self.collection, {"email": email}, policy=CachePolicy.AUTO
        )

    async def update_user(
        self: UsersOps, user_id: str, updates: dict[str, Any]
    ) -> bool:
        """Update user data.

        Args:
        ----
            user_id: User ID.
            updates: Update dictionary.

        Returns:
        -------
            True if successful, False otherwise.

        """
        updates = {**updates, "updated_at": datetime.now(timezone.utc)}
        return await self.service.set(
            self.collection, {"id": user_id}, updates, policy=CachePolicy.DB_ONLY
        )

    async def delete_user(self: UsersOps, user_id: str) -> bool:
        """Delete user.

        Args:
        ----
            user_id: User ID.

        Returns:
        -------
            True if successful, False otherwise.

        """
        return await self.service.delete(
            self.collection, {"id": user_id}, policy=CachePolicy.DB_ONLY
        )

    async def assign_roles(self: UsersOps, user_id: str, roles: list[str]) -> bool:
        """Assign roles to user.

        Args:
        ----
            user_id: User ID.
            roles: List of role IDs.

        Returns:
        -------
            True if successful, False otherwise.

        """
        return await self.update_user(user_id, {"roles": roles})

    async def assign_groups(self: UsersOps, user_id: str, groups: list[str]) -> bool:
        """Assign groups to user.

        Args:
        ----
            user_id: User ID.
            groups: List of group IDs.

        Returns:
        -------
            True if successful, False otherwise.

        """
        return await self.update_user(user_id, {"groups": groups})
