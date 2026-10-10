"""Authentication session management routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_data_service
from app.models.auth import ProfileUpdate
from app.models.user import UserPublic
from app.services.data import DataService
from app.utils.permissions import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me", response_model=UserPublic)
async def get_current_user_info(
    current_user=Depends(get_current_user),
    data_service: DataService = Depends(get_data_service),
) -> UserPublic:
    """Get current user information with resolved permissions.

    Args:
    ----
        current_user: Current authenticated user (TokenPayload)
        auth_service: Auth service instance

    Returns:
    -------
        Current user information

    Raises:
    ------
        HTTPException: If user info retrieval fails

    """
    try:
        # Get user from data service
        user_id = (
            current_user.user_id if hasattr(current_user, "user_id") else current_user["user_id"]
        )
        user_data = await data_service.users.get_user_by_id(user_id)

        if not user_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Return public user data
        return UserPublic(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            roles=user_data.get("roles", []),
            groups=user_data.get("groups", []),
            metadata=user_data.get("profile") or {},
            status=user_data.get("status", "active"),
            created_at=user_data.get("created_at"),
            updated_at=user_data.get("updated_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information",
        ) from e


@router.patch("/me", response_model=UserPublic)
async def update_my_profile(
    update: ProfileUpdate,
    current_user=Depends(get_current_user),
    data_service: DataService = Depends(get_data_service),
) -> UserPublic:
    """Change your own display name."""
    record = await data_service.users.get_user_by_id(current_user.user_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    profile = {**(record.get("profile") or {}), **update.model_dump(exclude_none=True)}
    await data_service.users.update_user(current_user.user_id, {"profile": profile})
    return await get_current_user_info(current_user, data_service)


__all__ = ["router"]
