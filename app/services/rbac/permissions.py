"""RBAC permission resolution functionality."""

from __future__ import annotations

from datetime import datetime, timezone

from app.services.data import DataService
from app.services.logger import Logger


class RBACPermissions:
    """RBAC permission resolution functionality."""

    def __init__(self, data_service: DataService, logger: Logger):
        """Initialize RBAC permissions.

        Args:
        ----
            data_service: Data service instance
            logger: Logger instance

        """
        self.data_service = data_service
        self.logger = logger

    async def resolve_user_permissions(
        self,
        user_id: str,
        user_roles: list[str],
        user_groups: list[str],
        core,
    ) -> list[str]:
        """Resolve all permissions for a user.

        Args:
        ----
            user_id: User identifier
            user_roles: User roles
            user_groups: User groups
            core: RBAC core instance

        Returns:
        -------
            List of resolved permissions

        """
        permissions = set()

        # Add permissions from direct roles
        for role_id in user_roles:
            role_permissions = await core.resolve_role_inheritance(role_id)
            permissions.update(role_permissions)

        # Add permissions from groups
        for group_id in user_groups:
            group = await self.data_service.rbac.get_group(group_id)
            if group:
                for role_id in group.get("roles", []):
                    role_permissions = await core.resolve_role_inheritance(role_id)
                    permissions.update(role_permissions)

        # Add temporary permissions
        temp_permissions = (
            await self.data_service.rbac.get_active_temporary_permissions(
                "user", user_id
            )
        )
        for temp_perm in temp_permissions:
            permissions.add(temp_perm["permission_id"])

        permission_list = list(permissions)

        self.logger.debug(
            f"User permissions resolved: {user_id}",
            extra={
                "action": "resolve_user_permissions",
                "user_id": user_id,
                "permission_count": len(permission_list),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return permission_list

    async def check_permission(
        self, user_permissions: list[str], permission: str
    ) -> bool:
        """Check if user has permission.

        Args:
        ----
            user_permissions: User's resolved permissions
            permission: Permission to check

        Returns:
        -------
            True if user has permission

        """
        # Check for wildcard permission
        if "*" in user_permissions:
            return True

        # Check specific permission
        has_permission = permission in user_permissions

        return has_permission


__all__ = ["RBACPermissions"]
