"""User management demo showcasing comprehensive user operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.class_store import get_class_store

if TYPE_CHECKING:
    from app.services.data import DataService
    from app.services.logger import Logger
    from app.services.rbac import RBACService
    from config import Config

class_store = get_class_store()


@class_store.register(name="user_management_demo")
class UserManagementDemo:
    """Demo class showcasing comprehensive user management operations.

    Demonstrates user CRUD operations, role/group assignment, and
    permission resolution using real services.
    """

    def __init__(
        self: UserManagementDemo,
        data_service: DataService | None = None,
        logger: Logger | None = None,
        config: Config | None = None,
    ):
        """Initialize UserManagementDemo with service injection.

        Args:
        ----
            data_service: Data service (auto-injected)
            logger: Logger service (auto-injected)
            config: Config service (auto-injected)

        """
        self.data_service = data_service
        self.logger = logger
        self.config = config
        self._rbac_service: RBACService | None = None

    def _get_rbac_service(self: UserManagementDemo) -> RBACService | None:
        """Get RBAC service from ClassStore.

        Returns
        -------
            RBACService instance or None if not available.

        """
        if self._rbac_service is None:
            try:
                class_store_instance = get_class_store()
                self._rbac_service = class_store_instance.get_service("rbac_service")
            except LookupError:
                if self.logger:
                    self.logger.warning("RBAC service not available")
        return self._rbac_service

    async def create_demo_user(
        self: UserManagementDemo, user_data: dict[str, Any]
    ) -> str:
        """Create a new user with sample data.

        Args:
        ----
            user_data: User data dictionary with username, email, etc.

        Returns:
        -------
            Created user ID.

        """
        if not self.data_service:
            raise ValueError("DataService not available")

        user_id = await self.data_service.create_user(user_data)

        if self.logger:
            self.logger.info(
                f"Created demo user: {user_id}",
                extra={"user_id": user_id, "username": user_data.get("username")},
            )

        return user_id

    async def get_user_by_identifier(
        self: UserManagementDemo, identifier: str
    ) -> dict[str, Any] | None:
        """Get user by ID, username, or email.

        Args:
        ----
            identifier: User ID, username, or email.

        Returns:
        -------
            User dictionary or None if not found.

        """
        if not self.data_service:
            raise ValueError("DataService not available")

        user = await self.data_service.get_user_by_id(identifier)
        if user:
            return user

        user = await self.data_service.get_user_by_username(identifier)
        if user:
            return user

        user = await self.data_service.get_user_by_email(identifier)
        return user

    async def update_user_profile(
        self: UserManagementDemo, user_id: str, updates: dict[str, Any]
    ) -> bool:
        """Update user profile information.

        Args:
        ----
            user_id: User ID.
            updates: Dictionary of fields to update.

        Returns:
        -------
            True if successful, False otherwise.

        """
        if not self.data_service:
            raise ValueError("DataService not available")

        result = await self.data_service.update_user(user_id, updates)

        if self.logger:
            self.logger.info(
                f"Updated user profile: {user_id}",
                extra={"user_id": user_id, "updated_fields": list(updates.keys())},
            )

        return result

    async def assign_user_roles(
        self: UserManagementDemo, user_id: str, role_ids: list[str]
    ) -> bool:
        """Assign roles to user.

        Args:
        ----
            user_id: User ID.
            role_ids: List of role IDs to assign.

        Returns:
        -------
            True if successful, False otherwise.

        """
        if not self.data_service:
            raise ValueError("DataService not available")

        result = await self.data_service.users.assign_roles(user_id, role_ids)

        if self.logger:
            self.logger.info(
                f"Assigned roles to user: {user_id}",
                extra={"user_id": user_id, "roles": role_ids},
            )

        return result

    async def assign_user_groups(
        self: UserManagementDemo, user_id: str, group_ids: list[str]
    ) -> bool:
        """Assign groups to user.

        Args:
        ----
            user_id: User ID.
            group_ids: List of group IDs to assign.

        Returns:
        -------
            True if successful, False otherwise.

        """
        if not self.data_service:
            raise ValueError("DataService not available")

        result = await self.data_service.users.assign_groups(user_id, group_ids)

        if self.logger:
            self.logger.info(
                f"Assigned groups to user: {user_id}",
                extra={"user_id": user_id, "groups": group_ids},
            )

        return result

    async def get_user_with_permissions(
        self: UserManagementDemo, user_id: str
    ) -> dict[str, Any]:
        """Get user with resolved permissions.

        Args:
        ----
            user_id: User ID.

        Returns:
        -------
            User dictionary with resolved permissions.

        """
        if not self.data_service:
            raise ValueError("DataService not available")

        user = await self.data_service.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        rbac_service = self._get_rbac_service()
        if rbac_service:
            permissions = await rbac_service.resolve_user_permissions(user_id)
            user["resolved_permissions"] = permissions

        return user

    async def list_all_users(self: UserManagementDemo) -> list[dict[str, Any]]:
        """List all users in the system.

        Returns
        -------
            List of user dictionaries.

        """
        if not self.data_service:
            raise ValueError("DataService not available")

        users = await self.data_service.find_many("users", {})

        if self.logger:
            self.logger.debug(
                f"Listed {len(users)} users",
                extra={"user_count": len(users)},
            )

        return users or []

    async def delete_user_safely(self: UserManagementDemo, user_id: str) -> bool:
        """Delete user with validation.

        Args:
        ----
            user_id: User ID.

        Returns:
        -------
            True if successful, False otherwise.

        """
        if not self.data_service:
            raise ValueError("DataService not available")

        user = await self.data_service.get_user_by_id(user_id)
        if not user:
            if self.logger:
                self.logger.warning(f"User not found for deletion: {user_id}")
            return False

        result = await self.data_service.delete_user(user_id)

        if self.logger:
            self.logger.info(
                f"Deleted user: {user_id}",
                extra={"user_id": user_id, "username": user.get("username")},
            )

        return result
