"""MongoDB user repository implementation."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.interfaces.user_repository_interface import UserRepositoryInterface
from app.services.database_service import DatabaseService
from app.services.logger import Logger


class UserRepository(UserRepositoryInterface):
    """MongoDB implementation of user repository."""

    def __init__(self, database_service: DatabaseService, logger: Logger):
        """Initialize user repository.

        Args:
        ----
            database_service: Database service instance
            logger: Logger instance

        """
        self.database_service = database_service
        self.logger = logger
        self.collection = "users"

    async def create_user(self, user_data: dict) -> str:
        """Create a new user.

        Args:
        ----
            user_data: User data dictionary

        Returns:
        -------
            Created user data

        """
        user_id = str(uuid.uuid4())
        user_data["id"] = user_id
        user_data["created_at"] = datetime.now(timezone.utc)
        user_data["updated_at"] = datetime.now(timezone.utc)

        await self.database_service.insert_record(self.collection, user_data)

        self.logger.info(
            f"User created: {user_id}",
            extra={
                "action": "create_user",
                "user_id": user_id,
                "username": user_data.get("username"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return user_id

    async def get_user_by_id(self, user_id: str) -> dict | None:
        """Get user by ID.

        Args:
        ----
            user_id: User identifier

        Returns:
        -------
            User data or None if not found

        """
        user = await self.database_service.get_record(self.collection, {"id": user_id})

        if user:
            self.logger.debug(
                f"User retrieved by ID: {user_id}",
                extra={
                    "action": "get_user_by_id",
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        else:
            self.logger.debug(
                f"User not found by ID: {user_id}",
                extra={
                    "action": "get_user_by_id",
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        return user

    async def get_user_by_username(self, username: str) -> dict | None:
        """Get user by username.

        Args:
        ----
            username: Username

        Returns:
        -------
            User data or None if not found

        """
        user = await self.database_service.get_record(
            self.collection, {"username": username}
        )

        if user:
            self.logger.debug(
                f"User retrieved by username: {username}",
                extra={
                    "action": "get_user_by_username",
                    "username": username,
                    "user_id": user.get("id"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        else:
            self.logger.debug(
                f"User not found by username: {username}",
                extra={
                    "action": "get_user_by_username",
                    "username": username,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        return user

    async def get_user_by_email(self, email: str) -> dict | None:
        """Get user by email.

        Args:
        ----
            email: Email address

        Returns:
        -------
            User data or None if not found

        """
        user = await self.database_service.get_record(self.collection, {"email": email})

        if user:
            self.logger.debug(
                f"User retrieved by email: {email}",
                extra={
                    "action": "get_user_by_email",
                    "email": email,
                    "user_id": user.get("id"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        else:
            self.logger.debug(
                f"User not found by email: {email}",
                extra={
                    "action": "get_user_by_email",
                    "email": email,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        return user

    async def update_user(self, user_id: str, updates: dict) -> bool:
        """Update user data.

        Args:
        ----
            user_id: User identifier
            updates: Update data dictionary

        Returns:
        -------
            True if updated successfully

        """
        updates["updated_at"] = datetime.now(timezone.utc)

        result = await self.database_service.update_record(
            self.collection, {"id": user_id}, updates
        )

        if result:
            self.logger.info(
                f"User updated: {user_id}",
                extra={
                    "action": "update_user",
                    "user_id": user_id,
                    "updates": list(updates.keys()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        else:
            self.logger.warning(
                f"User update failed: {user_id}",
                extra={
                    "action": "update_user",
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        return result

    async def delete_user(self, user_id: str) -> bool:
        """Delete user.

        Args:
        ----
            user_id: User identifier

        Returns:
        -------
            True if deleted successfully

        """
        result = await self.database_service.delete_record(
            self.collection, {"id": user_id}
        )

        if result:
            self.logger.info(
                f"User deleted: {user_id}",
                extra={
                    "action": "delete_user",
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        else:
            self.logger.warning(
                f"User deletion failed: {user_id}",
                extra={
                    "action": "delete_user",
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        return result

    async def assign_roles(self, user_id: str, roles: list[str]) -> bool:
        """Assign roles to user.

        Args:
        ----
            user_id: User identifier
            roles: List of role IDs

        Returns:
        -------
            True if assigned successfully

        """
        result = await self.update_user(user_id, {"roles": roles})

        if result:
            self.logger.info(
                f"Roles assigned to user: {user_id}",
                extra={
                    "action": "assign_roles",
                    "user_id": user_id,
                    "roles": roles,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        return result

    async def assign_groups(self, user_id: str, groups: list[str]) -> bool:
        """Assign groups to user.

        Args:
        ----
            user_id: User identifier
            groups: List of group IDs

        Returns:
        -------
            True if assigned successfully

        """
        result = await self.update_user(user_id, {"groups": groups})

        if result:
            self.logger.info(
                f"Groups assigned to user: {user_id}",
                extra={
                    "action": "assign_groups",
                    "user_id": user_id,
                    "groups": groups,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        return result


__all__ = ["UserRepository"]
