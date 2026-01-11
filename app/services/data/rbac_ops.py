from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from .policies import CachePolicy

if TYPE_CHECKING:
    from .data_service import DataService


class RBACOps:
    """RBAC-related data operations using core CRUD with cache policy."""

    def __init__(self: RBACOps, data_service: DataService) -> None:
        """Initialize RBACOps.

        Args:
        ----
            data_service: DataService instance.

        """
        self.ds = data_service
        self.roles_collection = "roles"
        self.permissions_collection = "permissions"
        self.groups_collection = "groups"
        self.temp_permissions_collection = "temporary_permissions"
        self.cache_ttl = 1800

    def _role_cache_key(self: RBACOps, role_id: str) -> str:
        """Generate cache key for role.

        Args:
        ----
            role_id: Role ID.

        Returns:
        -------
            Cache key string.

        """
        return f"role:{role_id}"

    def _permission_cache_key(self: RBACOps, permission_id: str) -> str:
        """Generate cache key for permission.

        Args:
        ----
            permission_id: Permission ID.

        Returns:
        -------
            Cache key string.

        """
        return f"permission:{permission_id}"

    def _group_cache_key(self: RBACOps, group_id: str) -> str:
        """Generate cache key for group.

        Args:
        ----
            group_id: Group ID.

        Returns:
        -------
            Cache key string.

        """
        return f"group:{group_id}"

    async def sync_roles_to_db(self: RBACOps, roles: dict[str, Any]) -> bool:
        """Sync roles from config to database.

        Args:
        ----
            roles: Roles dictionary from config.

        Returns:
        -------
            True if successful, False otherwise.

        """
        synced_count = 0
        now = datetime.now(timezone.utc)

        for role_id, role_data in roles.items():
            role_data["id"] = role_id
            role_data["synced_at"] = now

            await self.ds.set(
                self.roles_collection,
                {"id": role_id},
                role_data,
                policy=CachePolicy.DB_ONLY,
            )

            # Clear cache
            await self.ds.delete(
                self.roles_collection,
                {"id": role_id},
                policy=CachePolicy.CACHE_ONLY,
                key=self._role_cache_key(role_id),
            )

            synced_count += 1

        return True

    async def sync_permissions_to_db(
        self: RBACOps, permissions: dict[str, Any]
    ) -> bool:
        """Sync permissions from config to database.

        Args:
        ----
            permissions: Permissions dictionary from config.

        Returns:
        -------
            True if successful, False otherwise.

        """
        synced_count = 0
        now = datetime.now(timezone.utc)

        for perm_id, perm_data in permissions.items():
            perm_data["id"] = perm_id
            perm_data["synced_at"] = now

            await self.ds.set(
                self.permissions_collection,
                {"id": perm_id},
                perm_data,
                policy=CachePolicy.DB_ONLY,
            )

            # Clear cache
            await self.ds.delete(
                self.permissions_collection,
                {"id": perm_id},
                policy=CachePolicy.CACHE_ONLY,
                key=self._permission_cache_key(perm_id),
            )

            synced_count += 1

        return True

    async def sync_groups_to_db(self: RBACOps, groups: dict[str, Any]) -> bool:
        """Sync groups from config to database.

        Args:
        ----
            groups: Groups dictionary from config.

        Returns:
        -------
            True if successful, False otherwise.

        """
        synced_count = 0
        now = datetime.now(timezone.utc)

        for group_id, group_data in groups.items():
            group_data["id"] = group_id
            group_data["synced_at"] = now

            await self.ds.set(
                self.groups_collection,
                {"id": group_id},
                group_data,
                policy=CachePolicy.DB_ONLY,
            )

            # Clear cache
            await self.ds.delete(
                self.groups_collection,
                {"id": group_id},
                policy=CachePolicy.CACHE_ONLY,
                key=self._group_cache_key(group_id),
            )

            synced_count += 1

        return True

    async def get_role(self: RBACOps, role_id: str) -> dict[str, Any] | None:
        """Get role by ID with cache-first strategy.

        Args:
        ----
            role_id: Role ID.

        Returns:
        -------
            Role dictionary or None if not found.

        """
        role = await self.ds.get(
            self.roles_collection,
            {"id": role_id},
            policy=CachePolicy.AUTO,
            key=self._role_cache_key(role_id),
        )
        return role

    async def get_permission(
        self: RBACOps, permission_id: str
    ) -> dict[str, Any] | None:
        """Get permission by ID with cache-first strategy.

        Args:
        ----
            permission_id: Permission ID.

        Returns:
        -------
            Permission dictionary or None if not found.

        """
        permission = await self.ds.get(
            self.permissions_collection,
            {"id": permission_id},
            policy=CachePolicy.AUTO,
            key=self._permission_cache_key(permission_id),
        )
        return permission

    async def get_group(self: RBACOps, group_id: str) -> dict[str, Any] | None:
        """Get group by ID with cache-first strategy.

        Args:
        ----
            group_id: Group ID.

        Returns:
        -------
            Group dictionary or None if not found.

        """
        group = await self.ds.get(
            self.groups_collection,
            {"id": group_id},
            policy=CachePolicy.AUTO,
            key=self._group_cache_key(group_id),
        )
        return group

    async def create_temporary_permission(
        self: RBACOps, temp_perm: dict[str, Any]
    ) -> str:
        """Create temporary permission.

        Args:
        ----
            temp_perm: Temporary permission data dictionary.

        Returns:
        -------
            Temporary permission ID.

        """
        temp_perm_id = str(uuid.uuid4())
        temp_perm["id"] = temp_perm_id
        temp_perm["created_at"] = datetime.now(timezone.utc)

        await self.ds.set(
            self.temp_permissions_collection,
            {"id": temp_perm_id},
            temp_perm,
            policy=CachePolicy.DB_ONLY,
        )

        return temp_perm_id

    async def get_active_temporary_permissions(
        self: RBACOps, entity_type: str, entity_id: str
    ) -> list[dict[str, Any]]:
        """Get active temporary permissions for entity.

        Args:
        ----
            entity_type: Entity type (user or group).
            entity_id: Entity ID.

        Returns:
        -------
            List of temporary permission dictionaries.

        """
        now = datetime.now(timezone.utc)

        filters = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "$or": [
                {"end_time": {"$exists": False}},
                {"end_time": None},
                {"end_time": {"$gt": now}},
            ],
            "revoked_at": {"$exists": False},
        }

        temp_perms = await self.ds.find_many(
            self.temp_permissions_collection, filters, policy=CachePolicy.DB_ONLY
        )

        return temp_perms or []

    async def revoke_temporary_permission(self: RBACOps, temp_perm_id: str) -> bool:
        """Revoke temporary permission.

        Args:
        ----
            temp_perm_id: Temporary permission ID.

        Returns:
        -------
            True if successful, False otherwise.

        """
        updates = {"revoked_at": datetime.now(timezone.utc)}
        return await self.ds.set(
            self.temp_permissions_collection,
            {"id": temp_perm_id},
            updates,
            policy=CachePolicy.DB_ONLY,
        )
