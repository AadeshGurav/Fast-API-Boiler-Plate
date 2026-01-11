"""Permission workflow demo showcasing permission patterns and workflows."""

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


@class_store.register(name="permission_workflow_demo")
class PermissionWorkflowDemo:
    """Demo class showcasing permission workflows and patterns.

    Demonstrates permission checking, role inheritance, group-based
    permissions, and temporary permission management.
    """

    def __init__(
        self: PermissionWorkflowDemo,
        data_service: DataService | None = None,
        logger: Logger | None = None,
        config: Config | None = None,
    ):
        """Initialize PermissionWorkflowDemo with service injection.

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

    def _get_rbac_service(self: PermissionWorkflowDemo) -> RBACService:
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

    async def demonstrate_permission_check(
        self: PermissionWorkflowDemo, user_id: str, permission: str
    ) -> dict[str, Any]:
        """Demonstrate permission checking workflow.

        Args:
        ----
            user_id: User ID.
            permission: Permission to check.

        Returns:
        -------
            Dictionary with permission check details.

        """
        if not self.data_service:
            raise ValueError("DataService not available")

        rbac_service = self._get_rbac_service()

        user = await self.data_service.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        has_permission = await rbac_service.check_permission(user_id, permission)
        all_permissions = await rbac_service.resolve_user_permissions(user_id)

        result = {
            "user_id": user_id,
            "username": user.get("username"),
            "permission": permission,
            "has_permission": has_permission,
            "all_permissions": all_permissions,
            "permission_in_list": permission in all_permissions,
        }

        if self.logger:
            self.logger.info(
                f"Permission check demonstration: {user_id} -> {permission}",
                extra={
                    "user_id": user_id,
                    "permission": permission,
                    "result": has_permission,
                },
            )

        return result

    async def demonstrate_role_inheritance(
        self: PermissionWorkflowDemo, role_id: str
    ) -> dict[str, Any]:
        """Demonstrate role inheritance resolution.

        Args:
        ----
            role_id: Role ID.

        Returns:
        -------
            Dictionary with role inheritance details.

        """
        if not self.data_service:
            raise ValueError("DataService not available")

        rbac_service = self._get_rbac_service()

        role = await self.data_service.rbac.get_role(role_id)
        if not role:
            raise ValueError(f"Role not found: {role_id}")

        inherited_permissions = await rbac_service.resolve_role_inheritance(role_id)
        direct_permissions = role.get("permissions", [])

        result = {
            "role_id": role_id,
            "role_name": role.get("name", role_id),
            "direct_permissions": direct_permissions,
            "inherited_permissions": inherited_permissions,
            "total_permissions": len(inherited_permissions),
            "inherits_from": role.get("inherits", []),
        }

        if self.logger:
            self.logger.info(
                f"Role inheritance demonstration: {role_id}",
                extra={
                    "role_id": role_id,
                    "direct_count": len(direct_permissions),
                    "inherited_count": len(inherited_permissions),
                },
            )

        return result

    async def demonstrate_group_permissions(
        self: PermissionWorkflowDemo, user_id: str
    ) -> dict[str, Any]:
        """Demonstrate group-based permission resolution.

        Args:
        ----
            user_id: User ID.

        Returns:
        -------
            Dictionary with group permission details.

        """
        if not self.data_service:
            raise ValueError("DataService not available")

        rbac_service = self._get_rbac_service()

        user = await self.data_service.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        user_groups = user.get("groups", [])
        group_permissions = []

        for group_id in user_groups:
            group = await self.data_service.rbac.get_group(group_id)
            if group:
                group_roles = group.get("roles", [])
                for role_id in group_roles:
                    role_permissions = await rbac_service.resolve_role_inheritance(
                        role_id
                    )
                    group_permissions.extend(role_permissions)

        all_permissions = await rbac_service.resolve_user_permissions(user_id)

        result = {
            "user_id": user_id,
            "username": user.get("username"),
            "groups": user_groups,
            "group_permissions": list(set(group_permissions)),
            "all_resolved_permissions": all_permissions,
            "permissions_from_groups": len(set(group_permissions)),
        }

        if self.logger:
            self.logger.info(
                f"Group permissions demonstration: {user_id}",
                extra={
                    "user_id": user_id,
                    "group_count": len(user_groups),
                    "group_permission_count": len(set(group_permissions)),
                },
            )

        return result

    async def demonstrate_temporary_permissions(
        self: PermissionWorkflowDemo, user_id: str, permission_id: str
    ) -> dict[str, Any]:
        """Demonstrate temporary permission management.

        Args:
        ----
            user_id: User ID.
            permission_id: Permission ID.

        Returns:
        -------
            Dictionary with temporary permission details.

        """
        if not self.data_service:
            raise ValueError("DataService not available")

        rbac_service = self._get_rbac_service()

        now = datetime.now(timezone.utc)
        end_time = now + timedelta(hours=24)

        temp_perm_data = {
            "entity_type": "user",
            "entity_id": user_id,
            "permission_id": permission_id,
            "start_time": now,
            "end_time": end_time,
        }

        temp_perm_id = await rbac_service.create_temporary_permission(temp_perm_data)

        permissions_before = await rbac_service.resolve_user_permissions(user_id)
        has_permission_after = await rbac_service.check_permission(
            user_id, permission_id
        )

        active_temp_perms = await rbac_service.get_active_temporary_permissions(
            "user", user_id
        )

        result = {
            "user_id": user_id,
            "permission_id": permission_id,
            "temporary_permission_id": temp_perm_id,
            "permissions_before": permissions_before,
            "has_permission_after": has_permission_after,
            "active_temporary_permissions": active_temp_perms,
            "created_at": now.isoformat(),
            "expires_at": end_time.isoformat(),
        }

        if self.logger:
            self.logger.info(
                f"Temporary permission demonstration: {user_id} -> {permission_id}",
                extra={
                    "user_id": user_id,
                    "permission_id": permission_id,
                    "temp_perm_id": temp_perm_id,
                },
            )

        return result

    async def get_permission_audit_trail(
        self: PermissionWorkflowDemo, user_id: str
    ) -> dict[str, Any]:
        """Get permission audit trail for user.

        Args:
        ----
            user_id: User ID.

        Returns:
        -------
            Dictionary with permission audit information.

        """
        if not self.data_service:
            raise ValueError("DataService not available")

        rbac_service = self._get_rbac_service()

        user = await self.data_service.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        user_roles = user.get("roles", [])
        user_groups = user.get("groups", [])
        resolved_permissions = await rbac_service.resolve_user_permissions(user_id)
        temp_permissions = await rbac_service.get_active_temporary_permissions(
            "user", user_id
        )

        role_audit = []
        for role_id in user_roles:
            role = await self.data_service.rbac.get_role(role_id)
            if role:
                role_permissions = await rbac_service.resolve_role_inheritance(role_id)
                role_audit.append(
                    {
                        "role_id": role_id,
                        "role_name": role.get("name", role_id),
                        "permissions": role_permissions,
                    }
                )

        group_audit = []
        for group_id in user_groups:
            group = await self.data_service.rbac.get_group(group_id)
            if group:
                group_roles = group.get("roles", [])
                group_audit.append(
                    {
                        "group_id": group_id,
                        "group_name": group.get("name", group_id),
                        "roles": group_roles,
                    }
                )

        audit_trail = {
            "user_id": user_id,
            "username": user.get("username"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "roles": role_audit,
            "groups": group_audit,
            "temporary_permissions": temp_permissions,
            "resolved_permissions": resolved_permissions,
            "permission_count": len(resolved_permissions),
        }

        if self.logger:
            self.logger.info(
                f"Generated permission audit trail: {user_id}",
                extra={
                    "user_id": user_id,
                    "permission_count": len(resolved_permissions),
                },
            )

        return audit_trail
