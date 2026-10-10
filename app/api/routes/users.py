"""User administration: list accounts, look one up, enable or disable it.

Gated by the ``users:read`` / ``users:write`` permissions (managers and admins by default).
Role and group assignment lives under ``/rbac``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_auth_service, get_data_service, get_rbac_service
from app.models.auth import TokenPayload
from app.models.user import UserListResponse, UserPublic, UserStatus, UserStatusUpdate
from app.services.auth import AuthService
from app.services.data import DataService
from app.services.rbac import RBACService
from app.utils.permissions import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


def _public(record: dict) -> UserPublic:
    profile = record.get("profile") or {}
    return UserPublic(**{**record, "metadata": record.get("metadata") or profile})


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    account_status: UserStatus | None = Query(None, alias="status"),
    _: TokenPayload = Depends(get_current_user),
    data_service: DataService = Depends(get_data_service),
) -> UserListResponse:
    """Accounts, newest first."""
    records, total = await data_service.users.list_users(
        limit=page_size,
        skip=(page - 1) * page_size,
        status=account_status.value if account_status else None,
    )
    return UserListResponse(
        users=[_public(r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
        has_next=page * page_size < total,
    )


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: str,
    _: TokenPayload = Depends(get_current_user),
    data_service: DataService = Depends(get_data_service),
) -> UserPublic:
    """One account."""
    record = await data_service.users.get_user_by_id(user_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _public(record)


@router.patch("/{user_id}", response_model=UserPublic)
async def set_user_status(
    user_id: str,
    update: UserStatusUpdate,
    actor: TokenPayload = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    data_service: DataService = Depends(get_data_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> UserPublic:
    """Activate or suspend an account; suspending signs the user out everywhere."""
    # users:write lets a manager manage ordinary accounts, not lock out the administrators.
    if await rbac_service.check_permission(user_id, "*") and not await rbac_service.allows(
        actor, "*"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can change an administrator account",
        )
    if user_id == actor.user_id and update.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot disable your own account"
        )
    if not await auth_service.set_user_status(user_id, update.status.value):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _public(await data_service.users.get_user_by_id(user_id, fresh=True))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    actor: TokenPayload = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """Permanently delete an account (administrators only: needs ``users:delete``)."""
    if user_id == actor.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account"
        )
    if not await auth_service.delete_user(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


__all__ = ["router"]
