"""RBAC caching functionality."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.cache import CacheService
    from app.services.logger import Logger


class RBACCache:
    """RBAC caching functionality."""

    def __init__(self: RBACCache, cache_service: CacheService, logger: Logger) -> None:
        """Initialize RBAC cache.

        Args:
        ----
            cache_service: Cache service instance
            logger: Logger instance

        """
        self.cache_service: CacheService = cache_service
        self.logger: Logger = logger

        # Cache TTL for resolved permissions
        # TODO: Make this configurable  # noqa: FIX002
        self.permission_cache_ttl: int = 300  # 5 minutes

    async def get_user_permissions(self: RBACCache, user_id: str) -> list[str] | None:
        """Get cached user permissions.

        Args:
        ----
            user_id: User identifier

        Returns:
        -------
            Cached permissions or None

        """
        cache_key: str = f"user_permissions:{user_id}"
        return await self.cache_service.get(cache_key)

    async def set_user_permissions(
        self: RBACCache, user_id: str, permissions: list[str]
    ) -> None:
        """Cache user permissions.

        Args:
        ----
            user_id: User identifier
            permissions: List of permissions

        """
        cache_key: str = f"user_permissions:{user_id}"
        await self.cache_service.set(
            cache_key, permissions, ttl=self.permission_cache_ttl
        )

    async def clear_user_permissions(self: RBACCache, user_id: str) -> None:
        """Clear cached user permissions.

        Args:
        ----
            user_id: User identifier

        """
        cache_key: str = f"user_permissions:{user_id}"
        await self.cache_service.delete(cache_key)

    async def clear_all_permissions(self: RBACCache) -> None:
        """Clear all permission cache."""
        await self.cache_service.clear_pattern("user_permissions:*")

    async def assign_role(self: RBACCache, user_id: str, role_id: str) -> None:
        """Handle role assignment cache invalidation.

        Args:
        ----
            user_id: User identifier
            role_id: Role identifier

        """
        await self.clear_user_permissions(user_id)

        self.logger.info(
            f"Role assigned to user: {user_id} -> {role_id}",
            extra={
                "action": "assign_role",
                "user_id": user_id,
                "role_id": role_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def remove_role(self: RBACCache, user_id: str, role_id: str) -> None:
        """Handle role removal cache invalidation.

        Args:
        ----
            user_id: User identifier
            role_id: Role identifier

        """
        await self.clear_user_permissions(user_id)

        self.logger.info(
            f"Role removed from user: {user_id} -> {role_id}",
            extra={
                "action": "remove_role",
                "user_id": user_id,
                "role_id": role_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def assign_group(self: RBACCache, user_id: str, group_id: str) -> None:
        """Handle group assignment cache invalidation.

        Args:
        ----
            user_id: User identifier
            group_id: Group identifier

        """
        await self.clear_user_permissions(user_id)

        self.logger.info(
            f"Group assigned to user: {user_id} -> {group_id}",
            extra={
                "action": "assign_group",
                "user_id": user_id,
                "group_id": group_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def create_temporary_permission(self: RBACCache, temp_perm: dict) -> None:
        """Handle temporary permission creation cache invalidation.

        Args:
        ----
            temp_perm: Temporary permission data

        """
        # Clear affected user permission cache
        if temp_perm.get("entity_type", "") == "user":
            await self.clear_user_permissions(temp_perm["entity_id"])


__all__ = ["RBACCache"]
