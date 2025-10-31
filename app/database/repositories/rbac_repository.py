"""MongoDB RBAC repository implementation."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.interfaces.rbac_repository_interface import RBACRepositoryInterface
from app.services.cache import CacheService
from app.services.database_service import DatabaseService
from app.services.logger import Logger


class RBACRepository(RBACRepositoryInterface):
    """MongoDB implementation of RBAC repository."""

    def __init__(
        self,
        database_service: DatabaseService,
        cache_service: CacheService,
        logger: Logger,
    ):
        """Initialize RBAC repository.

        Args:
            database_service: Database service instance
            cache_service: Cache service instance
            logger: Logger instance

        """
        self.database_service = database_service
        self.cache_service = cache_service
        self.logger = logger
        self.roles_collection = "roles"
        self.permissions_collection = "permissions"
        self.groups_collection = "groups"
        self.temp_permissions_collection = "temporary_permissions"
        self.cache_ttl = 1800  # 30 minutes

    async def sync_roles_to_db(self, roles: dict) -> bool:
        """Sync roles from config to database.

        Args:
            roles: Roles dictionary from config

        Returns:
            True if synced successfully

        """
        synced_count = 0

        for role_id, role_data in roles.items():
            role_data["id"] = role_id
            role_data["synced_at"] = datetime.now(timezone.utc)

            # Upsert role
            await self.database_service.upsert_record(
                self.roles_collection, {"id": role_id}, role_data
            )

            # Clear cache
            cache_key = f"role:{role_id}"
            await self.cache_service.delete(cache_key)

            synced_count += 1

        self.logger.info(
            f"Roles synced to database: {synced_count}",
            extra={
                "action": "sync_roles_to_db",
                "synced_count": synced_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return True

    async def sync_permissions_to_db(self, permissions: dict) -> bool:
        """Sync permissions from config to database.

        Args:
            permissions: Permissions dictionary from config

        Returns:
            True if synced successfully

        """
        synced_count = 0

        for perm_id, perm_data in permissions.items():
            perm_data["id"] = perm_id
            perm_data["synced_at"] = datetime.now(timezone.utc)

            # Upsert permission
            await self.database_service.upsert_record(
                self.permissions_collection, {"id": perm_id}, perm_data
            )

            # Clear cache
            cache_key = f"permission:{perm_id}"
            await self.cache_service.delete(cache_key)

            synced_count += 1

        self.logger.info(
            f"Permissions synced to database: {synced_count}",
            extra={
                "action": "sync_permissions_to_db",
                "synced_count": synced_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return True

    async def sync_groups_to_db(self, groups: dict) -> bool:
        """Sync groups from config to database.

        Args:
            groups: Groups dictionary from config

        Returns:
            True if synced successfully

        """
        synced_count = 0

        for group_id, group_data in groups.items():
            group_data["id"] = group_id
            group_data["synced_at"] = datetime.now(timezone.utc)

            # Upsert group
            await self.database_service.upsert_record(
                self.groups_collection, {"id": group_id}, group_data
            )

            # Clear cache
            cache_key = f"group:{group_id}"
            await self.cache_service.delete(cache_key)

            synced_count += 1

        self.logger.info(
            f"Groups synced to database: {synced_count}",
            extra={
                "action": "sync_groups_to_db",
                "synced_count": synced_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return True

    async def get_role(self, role_id: str) -> dict | None:
        """Get role by ID.

        Args:
            role_id: Role identifier

        Returns:
            Role data or None if not found

        """
        # Try cache first
        cache_key = f"role:{role_id}"
        role = await self.cache_service.get(cache_key)

        if role:
            return role

        # Fallback to database
        role = await self.database_service.get_record(
            self.roles_collection, {"id": role_id}
        )

        if role:
            # Cache the result
            await self.cache_service.set(cache_key, role, ttl=self.cache_ttl)

        return role

    async def get_permission(self, permission_id: str) -> dict | None:
        """Get permission by ID.

        Args:
            permission_id: Permission identifier

        Returns:
            Permission data or None if not found

        """
        # Try cache first
        cache_key = f"permission:{permission_id}"
        permission = await self.cache_service.get(cache_key)

        if permission:
            return permission

        # Fallback to database
        permission = await self.database_service.get_record(
            self.permissions_collection, {"id": permission_id}
        )

        if permission:
            # Cache the result
            await self.cache_service.set(cache_key, permission, ttl=self.cache_ttl)

        return permission

    async def get_group(self, group_id: str) -> dict | None:
        """Get group by ID.

        Args:
            group_id: Group identifier

        Returns:
            Group data or None if not found

        """
        # Try cache first
        cache_key = f"group:{group_id}"
        group = await self.cache_service.get(cache_key)

        if group:
            return group

        # Fallback to database
        group = await self.database_service.get_record(
            self.groups_collection, {"id": group_id}
        )

        if group:
            # Cache the result
            await self.cache_service.set(cache_key, group, ttl=self.cache_ttl)

        return group

    async def create_temporary_permission(self, temp_perm: dict) -> str:
        """Create temporary permission.

        Args:
            temp_perm: Temporary permission data

        Returns:
            Temporary permission ID

        """
        temp_perm_id = str(uuid.uuid4())
        temp_perm["id"] = temp_perm_id
        temp_perm["created_at"] = datetime.now(timezone.utc)

        await self.database_service.insert_record(
            self.temp_permissions_collection, temp_perm
        )

        self.logger.info(
            f"Temporary permission created: {temp_perm_id}",
            extra={
                "action": "create_temporary_permission",
                "temp_perm_id": temp_perm_id,
                "entity_type": temp_perm.get("entity_type"),
                "entity_id": temp_perm.get("entity_id"),
                "permission_id": temp_perm.get("permission_id"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return temp_perm_id

    async def get_active_temporary_permissions(
        self, entity_type: str, entity_id: str
    ) -> list[dict]:
        """Get active temporary permissions for entity.

        Args:
            entity_type: Entity type (user or group)
            entity_id: Entity identifier

        Returns:
            List of active temporary permissions

        """
        now = datetime.now(timezone.utc)

        # Use MongoDB query instead of SQL
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

        # Get all matching records
        temp_perms = []
        try:
            # Use find_many for proper MongoDB query
            temp_perms = await self.database_service.find_many(
                self.temp_permissions_collection, filters
            )
        except Exception as e:
            self.logger.warning(
                f"Failed to get temporary permissions: {str(e)}",
                extra={
                    "action": "get_active_temporary_permissions",
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "error": str(e),
                },
            )

        self.logger.debug(
            f"Active temporary permissions retrieved: {entity_type}:{entity_id}",
            extra={
                "action": "get_active_temporary_permissions",
                "entity_type": entity_type,
                "entity_id": entity_id,
                "count": len(temp_perms) if temp_perms else 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return temp_perms or []

    async def revoke_temporary_permission(self, temp_perm_id: str) -> bool:
        """Revoke temporary permission.

        Args:
            temp_perm_id: Temporary permission identifier

        Returns:
            True if revoked successfully

        """
        result = await self.database_service.update_record(
            self.temp_permissions_collection,
            {"id": temp_perm_id},
            {"revoked_at": datetime.now(timezone.utc)},
        )

        if result:
            self.logger.info(
                f"Temporary permission revoked: {temp_perm_id}",
                extra={
                    "action": "revoke_temporary_permission",
                    "temp_perm_id": temp_perm_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        else:
            self.logger.warning(
                f"Temporary permission revocation failed: {temp_perm_id}",
                extra={
                    "action": "revoke_temporary_permission",
                    "temp_perm_id": temp_perm_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        return result


__all__ = ["RBACRepository"]
