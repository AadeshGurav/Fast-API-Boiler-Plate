"""RBAC service interface for platform-agnostic role-based access control operations."""
from __future__ import annotations

from abc import abstractmethod

from app.core.interfaces.base_interface import BaseInterface


class RBACServiceInterface(BaseInterface):
    """Interface for RBAC service operations."""

    @abstractmethod
    async def load_rbac_config(self) -> None:
        """Load RBAC configuration from config files."""
        pass

    @abstractmethod
    async def refresh_rbac_config(self) -> None:
        """Refresh RBAC configuration from config files."""
        pass

    @abstractmethod
    async def resolve_user_permissions(self, user_id: str) -> list[str]:
        """Resolve all permissions for a user.

        Args:
            user_id: User identifier

        Returns:
            List of resolved permissions

        """
        pass

    @abstractmethod
    async def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has permission.

        Args:
            user_id: User identifier
            permission: Permission to check

        Returns:
            True if user has permission

        """
        pass

    @abstractmethod
    async def resolve_role_inheritance(self, role_id: str) -> list[str]:
        """Resolve role inheritance recursively.

        Args:
            role_id: Role identifier

        Returns:
            List of inherited permissions

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
    async def assign_role(self, user_id: str, role_id: str) -> bool:
        """Assign role to user.

        Args:
            user_id: User identifier
            role_id: Role identifier

        Returns:
            True if assigned successfully

        """
        pass

    @abstractmethod
    async def remove_role(self, user_id: str, role_id: str) -> bool:
        """Remove role from user.

        Args:
            user_id: User identifier
            role_id: Role identifier

        Returns:
            True if removed successfully

        """
        pass

    @abstractmethod
    async def assign_group(self, user_id: str, group_id: str) -> bool:
        """Assign group to user.

        Args:
            user_id: User identifier
            group_id: Group identifier

        Returns:
            True if assigned successfully

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
    async def revoke_temporary_permission(self, temp_perm_id: str) -> bool:
        """Revoke temporary permission.

        Args:
            temp_perm_id: Temporary permission identifier

        Returns:
            True if revoked successfully

        """
        pass


__all__ = ["RBACServiceInterface"]
