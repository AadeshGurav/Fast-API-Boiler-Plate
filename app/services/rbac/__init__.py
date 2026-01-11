"""Main RBAC service combining all RBAC functionality."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from app.core.interfaces.rbac_service_interface import RBACServiceInterface
from app.services.base_service import BaseService
from app.services.rbac.cache import RBACCache
from app.services.rbac.core import RBACCore
from app.services.rbac.permissions import RBACPermissions

if TYPE_CHECKING:
    from app.services.cache import CacheService
    from app.services.data import DataService
    from app.services.logger import Logger
    from config import Config


class RBACService(RBACServiceInterface, BaseService):
    """RBAC service with JSON-driven configuration and caching."""

    def __init__(
        self: RBACService,
        config: Config,
        logger: Logger,
        data_service: DataService,
        cache_service: CacheService,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize RBAC service.

        Args:
        ----
            config: Configuration instance
            data_service: Data service instance
            cache_service: Cache service instance
            logger: Logger instance
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        """
        super().__init__(config, logger, *args, **kwargs)
        self.data_service: DataService = data_service

        # Initialize components
        self.core: RBACCore = RBACCore(config, data_service, logger)
        self.permissions: RBACPermissions = RBACPermissions(data_service, logger)
        self.cache: RBACCache = RBACCache(cache_service, logger)

    async def load_rbac_config(self: RBACService) -> None:
        """Load RBAC configuration from config files."""
        await self.core.load_rbac_config()

    async def refresh_rbac_config(self: RBACService) -> None:
        """Refresh RBAC configuration from config files."""
        await self.core.refresh_rbac_config()
        await self.cache.clear_all_permissions()

    async def resolve_user_permissions(self: RBACService, user_id: str) -> list[str]:
        """Resolve all permissions for a user.

        Args:
        ----
            user_id: User identifier

        Returns:
        -------
            List of resolved permissions

        """
        # Check cache first
        cached_permissions = await self.cache.get_user_permissions(user_id)
        if cached_permissions:
            return cached_permissions

        # Get user data from data service
        user_data = await self.data_service.users.get_user_by_id(user_id)
        user_roles: list[str] = user_data.get("roles", []) if user_data else []
        user_groups: list[str] = user_data.get("groups", []) if user_data else []

        # Resolve permissions
        permissions: list[str] = await self.permissions.resolve_user_permissions(
            user_id, user_roles, user_groups, self.core
        )

        # Cache the result
        await self.cache.set_user_permissions(user_id, permissions)

        return permissions

    async def check_permission(
        self: RBACService, user_id: str, permission: str
    ) -> bool:
        """Check if user has permission.

        Args:
        ----
            user_id: User identifier
            permission: Permission to check

        Returns:
        -------
            True if user has permission

        """
        user_permissions: list[str] = await self.resolve_user_permissions(user_id)
        has_permission: bool = await self.permissions.check_permission(
            user_permissions, permission
        )

        self.logger.debug(
            f"Permission check: {user_id} -> {permission}",
            extra={
                "action": "check_permission",
                "user_id": user_id,
                "permission": permission,
                "result": has_permission,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return has_permission

    async def resolve_role_inheritance(self: RBACService, role_id: str) -> list[str]:
        """Resolve role inheritance recursively with cycle detection.

        Args:
        ----
            role_id: Role identifier

        Returns:
        -------
            List of inherited permissions

        """
        return await self.core.resolve_role_inheritance(role_id)

    async def get_active_temporary_permissions(
        self: RBACService, entity_type: str, entity_id: str
    ) -> list[dict]:
        """Get active temporary permissions for entity.

        Args:
        ----
            entity_type: Entity type (user or group)
            entity_id: Entity identifier

        Returns:
        -------
            List of active temporary permissions

        """
        return await self.core.get_active_temporary_permissions(entity_type, entity_id)

    async def assign_role(self: RBACService, user_id: str, role_id: str) -> bool:
        """Assign role to user.

        Args:
        ----
            user_id: User identifier
            role_id: Role identifier

        Returns:
        -------
            True if assigned successfully

        """
        # Get current user roles
        user_data = await self.data_service.users.get_user_by_id(user_id)
        if not user_data:
            return False

        current_roles: list[str] = user_data.get("roles", [])
        if role_id not in current_roles:
            current_roles.append(role_id)

        # Update user roles
        result: bool = await self.data_service.users.assign_roles(
            user_id, current_roles
        )

        if result:
            await self.cache.assign_role(user_id, role_id)

        return result

    async def remove_role(self: RBACService, user_id: str, role_id: str) -> bool:
        """Remove role from user.

        Args:
        ----
            user_id: User identifier
            role_id: Role identifier

        Returns:
        -------
            True if removed successfully

        """
        # Get current user roles
        user_data = await self.data_service.users.get_user_by_id(user_id)
        if not user_data:
            return False

        current_roles: list[str] = user_data.get("roles", [])
        if role_id in current_roles:
            current_roles.remove(role_id)

        # Update user roles
        result: bool = await self.data_service.users.assign_roles(
            user_id, current_roles
        )

        if result:
            await self.cache.remove_role(user_id, role_id)

        return result

    async def assign_group(self: RBACService, user_id: str, group_id: str) -> bool:
        """Assign group to user.

        Args:
        ----
            user_id: User identifier
            group_id: Group identifier

        Returns:
        -------
            True if assigned successfully

        """
        # Get current user groups
        user_data = await self.data_service.users.get_user_by_id(user_id)
        if not user_data:
            return False

        current_groups: list[str] = user_data.get("groups", [])
        if group_id not in current_groups:
            current_groups.append(group_id)

        # Update user groups
        result: bool = await self.data_service.users.assign_groups(
            user_id, current_groups
        )

        if result:
            await self.cache.assign_group(user_id, group_id)

        return result

    async def create_temporary_permission(self: RBACService, temp_perm: dict) -> str:
        """Create temporary permission.

        Args:
        ----
            temp_perm: Temporary permission data

        Returns:
        -------
            Temporary permission ID

        """
        temp_perm_id: str = await self.core.create_temporary_permission(temp_perm)
        await self.cache.create_temporary_permission(temp_perm)
        return temp_perm_id

    async def revoke_temporary_permission(self: RBACService, temp_perm_id: str) -> bool:
        """Revoke temporary permission.

        Args:
        ----
            temp_perm_id: Temporary permission identifier

        Returns:
        -------
            True if revoked successfully

        """
        return await self.core.revoke_temporary_permission(temp_perm_id)


__all__ = ["RBACService"]
