"""RBAC repository interface for platform-agnostic role-based access control operations."""
from __future__ import annotations

from abc import abstractmethod

from app.core.interfaces.base_interface import BaseInterface


class RBACRepositoryInterface(BaseInterface):
    """Interface for RBAC repository operations."""

    @abstractmethod
    async def sync_roles_to_db(self, roles: dict) -> bool:
        """Sync roles from config to database.

        Args:
            roles: Roles dictionary from config

        Returns:
            True if synced successfully

        """
        pass

    @abstractmethod
    async def sync_permissions_to_db(self, permissions: dict) -> bool:
        """Sync permissions from config to database.

        Args:
            permissions: Permissions dictionary from config

        Returns:
            True if synced successfully

        """
        pass

    @abstractmethod
    async def sync_groups_to_db(self, groups: dict) -> bool:
        """Sync groups from config to database.

        Args:
            groups: Groups dictionary from config

        Returns:
            True if synced successfully

        """
        pass

    @abstractmethod
    async def get_role(self, role_id: str) -> dict | None:
        """Get role by ID.

        Args:
            role_id: Role identifier

        Returns:
            Role data or None if not found

        """
        pass

    @abstractmethod
    async def get_permission(self, permission_id: str) -> dict | None:
        """Get permission by ID.

        Args:
            permission_id: Permission identifier

        Returns:
            Permission data or None if not found

        """
        pass

    @abstractmethod
    async def get_group(self, group_id: str) -> dict | None:
        """Get group by ID.

        Args:
            group_id: Group identifier

        Returns:
            Group data or None if not found

        """
        pass

    @abstractmethod
    async def create_temporary_permission(self, temp_perm: dict) -> str:
        """Create temporary permission.

        Args:
            temp_perm: Temporary permission data

        Returns:
            Temporary permission ID

        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def revoke_temporary_permission(self, temp_perm_id: str) -> bool:
        """Revoke temporary permission.

        Args:
            temp_perm_id: Temporary permission identifier

        Returns:
            True if revoked successfully

        """
        pass


__all__ = ["RBACRepositoryInterface"]
