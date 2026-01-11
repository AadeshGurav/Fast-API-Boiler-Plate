"""RBAC management demo showcasing comprehensive RBAC operations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from app.core.class_store import get_class_store

if TYPE_CHECKING:
    from app.services.data import DataService
    from app.services.logger import Logger
    from app.services.rbac import RBACService
    from config import Config

class_store = get_class_store()


@class_store.register(name="rbac_management_demo")
class RBACManagementDemo:
    """Demo class showcasing comprehensive RBAC operations.

    Demonstrates role management, permission checking, group assignment,
    and temporary permissions using real services.
    """

    def __init__(
        self: RBACManagementDemo,
        data_service: DataService | None = None,
        logger: Logger | None = None,
        config: Config | None = None,
    ):
        """Initialize RBACManagementDemo with service injection.

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

    def _get_rbac_service(self: RBACManagementDemo) -> RBACService:
        """Get RBAC service from ClassStore.

        Returns:
        -------
            RBACService instance.

        Raises:
        ------
            ValueError: If RBAC service is not available.

        """
        if self._rbac_service is None:
            try:
                class_store_instance = get_class_store()
                self._rbac_service = class_store_instance.get_service("rbac_service")
            except LookupError:
                raise ValueError("RBAC service not available")
        return self._rbac_service

    async def get_role_details(
        self: RBACManagementDemo, role_id: str
    ) -> dict[str, Any]:
        """Get role details with inheritance resolution.

        Args:
        ----
            role_id: Role ID.

        Returns:
        -------
            Role dictionary with inherited permissions.

        """
        if not self.data_service:
            raise ValueError("DataService not available")

        role = await self.data_service.rbac.get_role(role_id)
        if not role:
            raise ValueError(f"Role not found: {role_id}")

        rbac_service = self._get_rbac_service()
        inherited_permissions = await rbac_service.resolve_role_inheritance(role_id)
        role["inherited_permissions"] = inherited_permissions

        if self.logger:
            self.logger.debug(
                f"Retrieved role details: {role_id}",
                extra={
                    "role_id": role_id,
                    "permission_count": len(inherited_permissions),
                },
            )

        return role

    async def check_user_permission(
        self: RBACManagementDemo, user_id: str, permission: str
    ) -> bool:
        """Check if user has specific permission.

        Args:
        ----
            user_id: User ID.
            permission: Permission to check.

        Returns:
        -------
            True if user has permission, False otherwise.

        """
        rbac_service = self._get_rbac_service()
        has_permission = await rbac_service.check_permission(user_id, permission)

        if self.logger:
            self.logger.debug(
                f"Permission check: {user_id} -> {permission}",
                extra={
                    "user_id": user_id,
                    "permission": permission,
                    "result": has_permission,
                },
            )

        return has_permission

    async def resolve_user_permissions(
        self: RBACManagementDemo, user_id: str
    ) -> list[str]:
        """Resolve all permissions for a user.

        Args:
        ----
            user_id: User ID.

        Returns:
        -------
            List of resolved permission IDs.

        """
        rbac_service = self._get_rbac_service()
        permissions = await rbac_service.resolve_user_permissions(user_id)

        if self.logger:
            self.logger.debug(
                f"Resolved permissions for user: {user_id}",
                extra={"user_id": user_id, "permission_count": len(permissions)},
            )

        return permissions

    async def assign_role_to_user(
        self: RBACManagementDemo, user_id: str, role_id: str
    ) -> bool:
        """Assign role to user.

        Args:
        ----
            user_id: User ID.
            role_id: Role ID.

        Returns:
        -------
            True if successful, False otherwise.

        """
        rbac_service = self._get_rbac_service()
        result = await rbac_service.assign_role(user_id, role_id)

        if self.logger:
            self.logger.info(
                f"Assigned role to user: {user_id}",
                extra={"user_id": user_id, "role_id": role_id, "success": result},
            )

        return result

    async def remove_role_from_user(
        self: RBACManagementDemo, user_id: str, role_id: str
    ) -> bool:
        """Remove role from user.

        Args:
        ----
            user_id: User ID.
            role_id: Role ID.

        Returns:
        -------
            True if successful, False otherwise.

        """
        rbac_service = self._get_rbac_service()
        result = await rbac_service.remove_role(user_id, role_id)

        if self.logger:
            self.logger.info(
                f"Removed role from user: {user_id}",
                extra={"user_id": user_id, "role_id": role_id, "success": result},
            )

        return result

    async def assign_group_to_user(
        self: RBACManagementDemo, user_id: str, group_id: str
    ) -> bool:
        """Assign group to user.

        Args:
        ----
            user_id: User ID.
            group_id: Group ID.

        Returns:
        -------
            True if successful, False otherwise.

        """
        rbac_service = self._get_rbac_service()
        result = await rbac_service.assign_group(user_id, group_id)

        if self.logger:
            self.logger.info(
                f"Assigned group to user: {user_id}",
                extra={"user_id": user_id, "group_id": group_id, "success": result},
            )

        return result

    async def create_temporary_permission(
        self: RBACManagementDemo,
        user_id: str,
        permission_id: str,
        duration_hours: int = 24,
    ) -> str:
        """Create temporary permission for user.

        Args:
        ----
            user_id: User ID.
            permission_id: Permission ID.
            duration_hours: Duration in hours (default: 24).

        Returns:
        -------
            Temporary permission ID.

        """
        rbac_service = self._get_rbac_service()

        now = datetime.now(timezone.utc)
        end_time = now + timedelta(hours=duration_hours)

        temp_perm_data = {
            "entity_type": "user",
            "entity_id": user_id,
            "permission_id": permission_id,
            "start_time": now,
            "end_time": end_time,
        }

        temp_perm_id = await rbac_service.create_temporary_permission(temp_perm_data)

        if self.logger:
            self.logger.info(
                f"Created temporary permission: {temp_perm_id}",
                extra={
                    "temp_perm_id": temp_perm_id,
                    "user_id": user_id,
                    "permission_id": permission_id,
                    "duration_hours": duration_hours,
                },
            )

        return temp_perm_id

    async def revoke_temporary_permission(
        self: RBACManagementDemo, temp_perm_id: str
    ) -> bool:
        """Revoke temporary permission.

        Args:
        ----
            temp_perm_id: Temporary permission ID.

        Returns:
        -------
            True if successful, False otherwise.

        """
        rbac_service = self._get_rbac_service()
        result = await rbac_service.revoke_temporary_permission(temp_perm_id)

        if self.logger:
            self.logger.info(
                f"Revoked temporary permission: {temp_perm_id}",
                extra={"temp_perm_id": temp_perm_id, "success": result},
            )

        return result

    async def get_user_permission_summary(
        self: RBACManagementDemo, user_id: str
    ) -> dict[str, Any]:
        """Get comprehensive permission summary for user.

        Args:
        ----
            user_id: User ID.

        Returns:
        -------
            Dictionary with permission summary.

        """
        if not self.data_service:
            raise ValueError("DataService not available")

        user = await self.data_service.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        rbac_service = self._get_rbac_service()

        user_roles = user.get("roles", [])
        user_groups = user.get("groups", [])
        resolved_permissions = await rbac_service.resolve_user_permissions(user_id)

        role_details = []
        for role_id in user_roles:
            role = await self.data_service.rbac.get_role(role_id)
            if role:
                role_details.append(role)

        group_details = []
        for group_id in user_groups:
            group = await self.data_service.rbac.get_group(group_id)
            if group:
                group_details.append(group)

        temp_permissions = await rbac_service.get_active_temporary_permissions(
            "user", user_id
        )

        summary = {
            "user_id": user_id,
            "username": user.get("username"),
            "roles": role_details,
            "groups": group_details,
            "resolved_permissions": resolved_permissions,
            "temporary_permissions": temp_permissions,
            "permission_count": len(resolved_permissions),
        }

        if self.logger:
            self.logger.debug(
                f"Generated permission summary for user: {user_id}",
                extra={
                    "user_id": user_id,
                    "permission_count": len(resolved_permissions),
                },
            )

        return summary
