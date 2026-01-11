"""RBAC management API routes for role/group/permission assignment."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.container import Container
from app.core.interfaces.rbac_service_interface import RBACServiceInterface
from app.models.role import TemporaryPermission
from app.utils.permissions import get_current_user

router = APIRouter(prefix="/rbac", tags=["RBAC Management"])


@router.get("/roles")
async def list_roles(
    current_user: dict = Depends(get_current_user),
    rbac_service: RBACServiceInterface = Depends(lambda: Container.rbac_service()),
):
    """List all available roles.

    Args:
    ----
        current_user: Current authenticated user
        rbac_service: RBAC service instance

    Returns:
    -------
        List of roles

    Raises:
    ------
        HTTPException: If user doesn't have permission

    """
    try:
        # Check permission
        has_permission = await rbac_service.check_permission(
            current_user["user_id"], "rbac:read"
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: rbac:read",
            )

        # Get roles from service
        roles = rbac_service.roles_cache

        return {"roles": roles}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve roles",
        ) from e


@router.get("/permissions")
async def list_permissions(
    current_user: dict = Depends(get_current_user),
    rbac_service: RBACServiceInterface = Depends(lambda: Container.rbac_service()),
):
    """List all available permissions.

    Args:
    ----
        current_user: Current authenticated user
        rbac_service: RBAC service instance

    Returns:
    -------
        List of permissions

    Raises:
    ------
        HTTPException: If user doesn't have permission

    """
    try:
        # Check permission
        has_permission = await rbac_service.check_permission(
            current_user["user_id"], "rbac:read"
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: rbac:read",
            )

        # Get permissions from service
        permissions = rbac_service.permissions_cache

        return {"permissions": permissions}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve permissions",
        ) from e


@router.get("/groups")
async def list_groups(
    current_user: dict = Depends(get_current_user),
    rbac_service: RBACServiceInterface = Depends(lambda: Container.rbac_service()),
):
    """List all available groups.

    Args:
    ----
        current_user: Current authenticated user
        rbac_service: RBAC service instance

    Returns:
    -------
        List of groups

    Raises:
    ------
        HTTPException: If user doesn't have permission

    """
    try:
        # Check permission
        has_permission = await rbac_service.check_permission(
            current_user["user_id"], "rbac:read"
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: rbac:read",
            )

        # Get groups from service
        groups = rbac_service.groups_cache

        return {"groups": groups}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve groups",
        ) from e


@router.post("/users/{user_id}/roles")
async def assign_role(
    user_id: str,
    role_id: str,
    current_user: dict = Depends(get_current_user),
    rbac_service: RBACServiceInterface = Depends(lambda: Container.rbac_service()),
):
    """Assign role to user.

    Args:
    ----
        user_id: Target user ID
        role_id: Role ID to assign
        current_user: Current authenticated user
        rbac_service: RBAC service instance

    Returns:
    -------
        Success message

    Raises:
    ------
        HTTPException: If user doesn't have permission or assignment fails

    """
    try:
        # Check permission
        has_permission = await rbac_service.check_permission(
            current_user["user_id"], "rbac:write"
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: rbac:write",
            )

        # Assign role
        success = await rbac_service.assign_role(user_id, role_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to assign role"
            )

        return {"message": f"Role {role_id} assigned to user {user_id}"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign role",
        ) from e


@router.delete("/users/{user_id}/roles/{role_id}")
async def remove_role(
    user_id: str,
    role_id: str,
    current_user: dict = Depends(get_current_user),
    rbac_service: RBACServiceInterface = Depends(lambda: Container.rbac_service()),
):
    """Remove role from user.

    Args:
    ----
        user_id: Target user ID
        role_id: Role ID to remove
        current_user: Current authenticated user
        rbac_service: RBAC service instance

    Returns:
    -------
        Success message

    Raises:
    ------
        HTTPException: If user doesn't have permission or removal fails

    """
    try:
        # Check permission
        has_permission = await rbac_service.check_permission(
            current_user["user_id"], "rbac:write"
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: rbac:write",
            )

        # Remove role
        success = await rbac_service.remove_role(user_id, role_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to remove role"
            )

        return {"message": f"Role {role_id} removed from user {user_id}"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove role",
        ) from e


@router.post("/users/{user_id}/groups")
async def assign_group(
    user_id: str,
    group_id: str,
    current_user: dict = Depends(get_current_user),
    rbac_service: RBACServiceInterface = Depends(lambda: Container.rbac_service()),
):
    """Assign group to user.

    Args:
    ----
        user_id: Target user ID
        group_id: Group ID to assign
        current_user: Current authenticated user
        rbac_service: RBAC service instance

    Returns:
    -------
        Success message

    Raises:
    ------
        HTTPException: If user doesn't have permission or assignment fails

    """
    try:
        # Check permission
        has_permission = await rbac_service.check_permission(
            current_user["user_id"], "rbac:write"
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: rbac:write",
            )

        # Assign group
        success = await rbac_service.assign_group(user_id, group_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to assign group"
            )

        return {"message": f"Group {group_id} assigned to user {user_id}"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign group",
        ) from e


@router.post("/temporary-permissions")
async def create_temporary_permission(
    temp_perm: TemporaryPermission,
    current_user: dict = Depends(get_current_user),
    rbac_service: RBACServiceInterface = Depends(lambda: Container.rbac_service()),
):
    """Create temporary permission.

    Args:
    ----
        temp_perm: Temporary permission data
        current_user: Current authenticated user
        rbac_service: RBAC service instance

    Returns:
    -------
        Created temporary permission ID

    Raises:
    ------
        HTTPException: If user doesn't have permission or creation fails

    """
    try:
        # Check permission
        has_permission = await rbac_service.check_permission(
            current_user["user_id"], "rbac:write"
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: rbac:write",
            )

        # Set created_by
        temp_perm.created_by = current_user["user_id"]

        # Create temporary permission
        temp_perm_id = await rbac_service.create_temporary_permission(temp_perm)

        return {"temp_permission_id": temp_perm_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create temporary permission",
        ) from e


@router.delete("/temporary-permissions/{temp_perm_id}")
async def revoke_temporary_permission(
    temp_perm_id: str,
    current_user: dict = Depends(get_current_user),
    rbac_service: RBACServiceInterface = Depends(lambda: Container.rbac_service()),
):
    """Revoke temporary permission.

    Args:
    ----
        temp_perm_id: Temporary permission ID
        current_user: Current authenticated user
        rbac_service: RBAC service instance

    Returns:
    -------
        Success message

    Raises:
    ------
        HTTPException: If user doesn't have permission or revocation fails

    """
    try:
        # Check permission
        has_permission = await rbac_service.check_permission(
            current_user["user_id"], "rbac:write"
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: rbac:write",
            )

        # Revoke temporary permission
        success = await rbac_service.revoke_temporary_permission(temp_perm_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to revoke temporary permission",
            )

        return {"message": f"Temporary permission {temp_perm_id} revoked"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke temporary permission",
        ) from e


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    rbac_service: RBACServiceInterface = Depends(lambda: Container.rbac_service()),
):
    """Get resolved permissions for user.

    Args:
    ----
        user_id: Target user ID
        current_user: Current authenticated user
        rbac_service: RBAC service instance

    Returns:
    -------
        List of resolved permissions

    Raises:
    ------
        HTTPException: If user doesn't have permission or retrieval fails

    """
    try:
        # Check permission
        has_permission = await rbac_service.check_permission(
            current_user["user_id"], "rbac:read"
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: rbac:read",
            )

        # Get resolved permissions
        permissions = await rbac_service.resolve_user_permissions(user_id)

        return {"permissions": permissions}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user permissions",
        ) from e
