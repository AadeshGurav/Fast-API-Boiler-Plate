"""RBAC management API: role, group and temporary-permission administration.

Every endpoint is also admin-only at the middleware level (``admin_only_paths``); the
per-endpoint ``rbac:read`` / ``rbac:write`` dependencies are a second, independent lock.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_rbac_service
from app.models.auth import TokenPayload
from app.models.role import TemporaryPermissionCreate
from app.services.rbac import RBACService
from app.utils.permissions import require_permission

router = APIRouter(prefix="/rbac", tags=["RBAC Management"])


def _not_found(what: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{what} not found")


@router.get("/roles")
async def list_roles(
    _: TokenPayload = Depends(require_permission("rbac:read")),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> dict[str, dict]:
    """List all roles."""
    return {"roles": rbac_service.roles}


@router.get("/permissions")
async def list_permissions(
    _: TokenPayload = Depends(require_permission("rbac:read")),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> dict[str, dict]:
    """List all permissions."""
    return {"permissions": rbac_service.permissions}


@router.get("/groups")
async def list_groups(
    _: TokenPayload = Depends(require_permission("rbac:read")),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> dict[str, dict]:
    """List all groups."""
    return {"groups": rbac_service.groups}


@router.post("/users/{user_id}/roles")
async def assign_role(
    user_id: str,
    role_id: str,
    _: TokenPayload = Depends(require_permission("rbac:write")),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> dict[str, str]:
    """Give a user a role."""
    if not await rbac_service.assign_role(user_id, role_id):
        raise _not_found("User or role")
    return {"message": f"Role {role_id} assigned to user {user_id}"}


@router.delete("/users/{user_id}/roles/{role_id}")
async def remove_role(
    user_id: str,
    role_id: str,
    _: TokenPayload = Depends(require_permission("rbac:write")),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> dict[str, str]:
    """Take a role away from a user."""
    if not await rbac_service.remove_role(user_id, role_id):
        raise _not_found("User")
    return {"message": f"Role {role_id} removed from user {user_id}"}


@router.post("/users/{user_id}/groups")
async def assign_group(
    user_id: str,
    group_id: str,
    _: TokenPayload = Depends(require_permission("rbac:write")),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> dict[str, str]:
    """Put a user in a group."""
    if not await rbac_service.assign_group(user_id, group_id):
        raise _not_found("User or group")
    return {"message": f"Group {group_id} assigned to user {user_id}"}


@router.post("/temporary-permissions", status_code=status.HTTP_201_CREATED)
async def create_temporary_permission(
    temp_perm: TemporaryPermissionCreate,
    admin: TokenPayload = Depends(require_permission("rbac:write")),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> dict[str, str]:
    """Grant a permission for a limited time."""
    temp_perm_id = await rbac_service.create_temporary_permission(
        {**temp_perm.model_dump(), "created_by": admin.user_id}
    )
    return {"temp_permission_id": temp_perm_id}


@router.delete("/temporary-permissions/{temp_perm_id}")
async def revoke_temporary_permission(
    temp_perm_id: str,
    _: TokenPayload = Depends(require_permission("rbac:write")),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> dict[str, str]:
    """Revoke a temporary permission before it expires."""
    if not await rbac_service.revoke_temporary_permission(temp_perm_id):
        raise _not_found("Temporary permission")
    return {"message": f"Temporary permission {temp_perm_id} revoked"}


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: str,
    _: TokenPayload = Depends(require_permission("rbac:read")),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> dict[str, list[str]]:
    """Show the permissions a user currently holds (roles, groups, temporary grants)."""
    return {"permissions": await rbac_service.resolve_user_permissions(user_id)}


__all__ = ["router"]
