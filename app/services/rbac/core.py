"""Core RBAC functionality."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.database.repositories.rbac_repository import RBACRepository
    from app.services.logger import Logger
    from config import Config


class RBACCore:
    """Core RBAC functionality."""

    def __init__(
        self: RBACCore, config: Config, rbac_repository: RBACRepository, logger: Logger
    ) -> None:
        """Initialize RBAC core.

        Args:
        ----
            config: Configuration instance
            rbac_repository: RBAC repository instance
            logger: Logger instance

        """
        self.config: Config = config
        self.rbac_repository: RBACRepository = rbac_repository
        self.logger: Logger = logger

        # In-memory cache for roles, permissions, groups
        self.roles_cache: dict[str, dict] = {}
        self.permissions_cache: dict[str, dict] = {}
        self.groups_cache: dict[str, dict] = {}

    async def load_rbac_config(self: RBACCore) -> None:
        """Load RBAC configuration from config files."""
        try:
            # Load roles from config
            roles_data: dict[str, dict] = self.config.get("rbac_roles", {})
            await self.rbac_repository.sync_roles_to_db(roles_data)
            self.roles_cache = roles_data

            # Load permissions from config
            permissions_data = self.config.get("rbac_permissions", {})
            await self.rbac_repository.sync_permissions_to_db(permissions_data)
            self.permissions_cache = permissions_data

            # Load groups from config
            groups_data = self.config.get("rbac_groups", {})
            await self.rbac_repository.sync_groups_to_db(groups_data)
            self.groups_cache = groups_data

            self.logger.info(
                f"RBAC configuration loaded: {len(roles_data)} roles, "
                f"{len(permissions_data)} permissions, {len(groups_data)} groups",
                extra={
                    "action": "load_rbac_config",
                    "roles_count": len(roles_data),
                    "permissions_count": len(permissions_data),
                    "groups_count": len(groups_data),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception as e:
            self.logger.error(
                f"Failed to load RBAC configuration: {str(e)}",
                extra={
                    "action": "load_rbac_config",
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            raise

    async def refresh_rbac_config(self) -> None:
        """Refresh RBAC configuration from config files."""
        try:
            # Reload config
            self.config.reload()

            # Reload RBAC data
            await self.load_rbac_config()

            self.logger.info(
                "RBAC configuration refreshed",
                extra={
                    "action": "refresh_rbac_config",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception as e:
            self.logger.error(
                f"Failed to refresh RBAC configuration: {str(e)}",
                extra={
                    "action": "refresh_rbac_config",
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            raise

    async def resolve_role_inheritance(self, role_id: str) -> list[str]:
        """Resolve role inheritance recursively with cycle detection.

        Args:
        ----
            role_id: Role identifier

        Returns:
        -------
            List of inherited permissions

        """
        visited = set()
        permissions = set()

        async def _resolve_role(role_id: str, path: list[str]):
            # Cycle detection
            if role_id in visited:
                self.logger.warning(
                    f"Role inheritance cycle detected: "
                    f"{' -> '.join(path)} -> {role_id}",
                    extra={
                        "action": "resolve_role_inheritance",
                        "cycle_path": path + [role_id],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                return

            visited.add(role_id)

            # Get role from cache or database
            role = self.roles_cache.get(role_id)
            if not role:
                role = await self.rbac_repository.get_role(role_id)

            if not role:
                return

            # Add direct permissions
            permissions.update(role.get("permissions", []))

            # Resolve inherited roles
            for inherited_role_id in role.get("inherits", []):
                await _resolve_role(inherited_role_id, path + [role_id])

        await _resolve_role(role_id, [])

        permission_list = list(permissions)

        self.logger.debug(
            f"Role inheritance resolved: {role_id}",
            extra={
                "action": "resolve_role_inheritance",
                "role_id": role_id,
                "permission_count": len(permission_list),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return permission_list

    async def get_active_temporary_permissions(
        self, entity_type: str, entity_id: str
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
        return await self.rbac_repository.get_active_temporary_permissions(
            entity_type, entity_id
        )

    async def create_temporary_permission(self, temp_perm: dict) -> str:
        """Create temporary permission.

        Args:
        ----
            temp_perm: Temporary permission data

        Returns:
        -------
            Temporary permission ID

        """
        temp_perm_id = await self.rbac_repository.create_temporary_permission(temp_perm)
        return temp_perm_id

    async def revoke_temporary_permission(self, temp_perm_id: str) -> bool:
        """Revoke temporary permission.

        Args:
        ----
            temp_perm_id: Temporary permission identifier

        Returns:
        -------
            True if revoked successfully

        """
        result = await self.rbac_repository.revoke_temporary_permission(temp_perm_id)

        if result:
            self.logger.info(
                f"Temporary permission revoked: {temp_perm_id}",
                extra={
                    "action": "revoke_temporary_permission",
                    "temp_perm_id": temp_perm_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        return result


__all__ = ["RBACCore"]
