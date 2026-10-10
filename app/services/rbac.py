"""Role-based access control.

One source of truth per kind of data:

* **Definitions** (roles, permissions, groups, inheritance) live in ``config.toml``
  and are held in memory. They are never copied into the database.
* **Assignments** (a user's roles and groups) live on the user record.
* **Temporary grants** live in the ``temporary_permissions`` collection.

A user's effective permissions are resolved from those three and cached per user; the cache
entry is dropped whenever any input changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.services.base_service import BaseService

if TYPE_CHECKING:
    from collections.abc import Iterable

    from app.models.auth import TokenPayload
    from app.services.audit import AuditService
    from app.services.cache import CacheService
    from app.services.data import DataService
    from app.services.logger import Logger
    from config import Config

PERMISSION_CACHE_PREFIX = "user_permissions:"
WILDCARD = "*"


def covers(held: Iterable[str], permission: str) -> bool:
    """Whether ``held`` grants ``permission``, honouring ``*`` and ``resource:*``."""
    held = set(held)
    resource = permission.partition(":")[0]
    return bool({WILDCARD, permission, f"{resource}:{WILDCARD}"} & held)


class RBACService(BaseService):
    """Resolve and check permissions; manage assignments and temporary grants."""

    def __init__(
        self,
        config: Config,
        logger: Logger,
        data_service: DataService,
        cache_service: CacheService,
        audit: AuditService,
    ) -> None:
        super().__init__(config, logger)
        self.data_service = data_service
        self.cache = cache_service
        self.audit = audit
        self.permission_ttl: int = config["rbac_permission_cache_ttl"]
        self.roles: dict[str, dict] = {}
        self.groups: dict[str, dict] = {}
        self.load_rbac_config()

    # ---- definitions (config) ---------------------------------------------------
    def load_rbac_config(self) -> None:
        """(Re)read role, permission and group definitions from configuration."""
        self.roles = dict(self.config["rbac_roles"])
        self.groups = dict(self.config["rbac_groups"])
        self.logger.info(f"RBAC loaded: {len(self.roles)} roles, {len(self.groups)} groups")

    async def refresh_rbac_config(self) -> None:
        """Reload configuration files and drop every cached permission set."""
        self.config.reload()
        self.load_rbac_config()
        await self.cache.clear_pattern(PERMISSION_CACHE_PREFIX)

    @property
    def permissions(self) -> dict[str, dict]:
        """Every permission mentioned by any role (they need no separate declaration)."""
        found = {p for role in self.roles for p in self.resolve_role_inheritance(role)}
        return {
            name: {"id": name, "resource": name.partition(":")[0], "action": name.partition(":")[2]}
            for name in sorted(found)
        }

    def resolve_role_inheritance(self, role_id: str) -> set[str]:
        """Permissions of a role including everything it inherits.

        A role that inherits from itself (directly or not) is a configuration error; the
        cycle is cut and logged rather than recursing forever. Diamonds (two roles
        inheriting the same parent) are legal.
        """
        permissions: set[str] = set()
        expanded: set[str] = set()

        def expand(current: str, path: tuple[str, ...]) -> None:
            if current in path:
                self.logger.warning(f"Role inheritance cycle: {' -> '.join((*path, current))}")
                return
            role = self.roles.get(current)
            if role is None or current in expanded:
                return
            expanded.add(current)
            permissions.update(role.get("permissions", []))
            for parent in role.get("inherits", []):
                expand(parent, (*path, current))

        expand(role_id, ())
        return permissions

    # ---- resolution ----------------------------------------------------------------
    async def resolve_user_permissions(self, user_id: str) -> list[str]:
        """Effective permissions: roles, group roles and active temporary grants."""
        key = f"{PERMISSION_CACHE_PREFIX}{user_id}"
        cached = await self.cache.get(key)
        if cached is not None:
            return cached

        user = await self.data_service.users.get_user_by_id(user_id) or {}
        permissions: set[str] = set()
        for role_id in user.get("roles", []):
            permissions |= self.resolve_role_inheritance(role_id)
        for group_id in user.get("groups", []):
            for role_id in self.groups.get(group_id, {}).get("roles", []):
                permissions |= self.resolve_role_inheritance(role_id)

        temp = self.data_service.temp_permissions
        grants = await temp.get_active("user", user_id)
        for group_id in user.get("groups", []):
            grants += await temp.get_active("group", group_id)
        permissions.update(grant["permission_id"] for grant in grants)

        result = sorted(permissions)
        await self.cache.set(key, result, ttl=self.permission_ttl)
        return result

    async def check_permission(self, user_id: str, permission: str) -> bool:
        """Whether the user holds ``permission``.

        ``*`` grants everything and ``resource:*`` grants every action on a resource.
        """
        return covers(await self.resolve_user_permissions(user_id), permission)

    async def allows(self, caller: TokenPayload, permission: str) -> bool:
        """Whether this request may use ``permission``: the user must hold it and, for an API
        token, the token's scopes must cover it too, so a token never exceeds its owner."""
        if caller.scopes is not None and not covers(caller.scopes, permission):
            return False
        return await self.check_permission(caller.user_id, permission)

    async def _forget(self, user_id: str) -> None:
        await self.cache.delete(f"{PERMISSION_CACHE_PREFIX}{user_id}")

    # ---- assignments (on the user record) ----------------------------------------
    async def _change_list(
        self, user_id: str, field: str, value: str, *, add: bool, known: dict[str, dict]
    ) -> bool:
        user = await self.data_service.users.get_user_by_id(user_id)
        if not user or (add and value not in known):
            return False
        current = list(user.get(field, []))
        if add and value not in current:
            current.append(value)
        elif not add and value in current:
            current.remove(value)
        updated = await self.data_service.users.update_user(user_id, {field: current})
        if updated:
            await self._forget(user_id)
        return updated

    async def _audited_change(
        self, action: str, user_id: str, field: str, value: str, *, add: bool, known: dict
    ) -> bool:
        changed = await self._change_list(user_id, field, value, add=add, known=known)
        if changed:
            await self.audit.record(
                action, target_type="user", target_id=user_id, details={field[:-1]: value}
            )
        return changed

    async def assign_role(self, user_id: str, role_id: str) -> bool:
        """Give a user a (defined) role."""
        return await self._audited_change(
            "rbac.role_assigned", user_id, "roles", role_id, add=True, known=self.roles
        )

    async def remove_role(self, user_id: str, role_id: str) -> bool:
        """Take a role away from a user."""
        return await self._audited_change(
            "rbac.role_removed", user_id, "roles", role_id, add=False, known=self.roles
        )

    async def assign_group(self, user_id: str, group_id: str) -> bool:
        """Put a user in a (defined) group."""
        return await self._audited_change(
            "rbac.group_assigned", user_id, "groups", group_id, add=True, known=self.groups
        )

    # ---- temporary grants ----------------------------------------------------------
    async def create_temporary_permission(self, grant: dict[str, Any]) -> str:
        """Grant a permission for a limited time; returns the grant id."""
        grant_id = await self.data_service.temp_permissions.create(grant)
        await self._forget_entity(grant["entity_type"], grant["entity_id"])
        await self.audit.record(
            "rbac.grant_created",
            target_type=grant["entity_type"],
            target_id=grant["entity_id"],
            details={"grant_id": grant_id, "permission": grant.get("permission_id")},
        )
        return grant_id

    async def revoke_temporary_permission(self, grant_id: str) -> bool:
        """Revoke a grant before it expires."""
        grant = await self.data_service.temp_permissions.get(grant_id)
        if not grant or not await self.data_service.temp_permissions.revoke(grant_id):
            return False
        await self._forget_entity(grant["entity_type"], grant["entity_id"])
        await self.audit.record(
            "rbac.grant_revoked",
            target_type=grant["entity_type"],
            target_id=grant["entity_id"],
            details={"grant_id": grant_id, "permission": grant.get("permission_id")},
        )
        return True

    async def _forget_entity(self, entity_type: str, entity_id: str) -> None:
        if entity_type == "user":
            await self._forget(entity_id)
        else:  # a group grant affects every member: no reverse index, so drop them all
            await self.cache.clear_pattern(PERMISSION_CACHE_PREFIX)


__all__ = ["RBACService"]
