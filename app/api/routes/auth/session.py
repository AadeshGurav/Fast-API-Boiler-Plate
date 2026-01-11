"""Authentication session management routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app import container as app_container
from app.models.user import UserPublic
from app.services.auth import AuthService
from app.services.data import DataService
from app.utils.permissions import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me", response_model=UserPublic)
async def get_current_user_info(
    current_user=Depends(get_current_user),
    auth_service: AuthService = Depends(lambda: app_container.auth_service()),
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
        data_service: DataService = app_container.data_service()
        user_id = (
            current_user.user_id
            if hasattr(current_user, "user_id")
            else current_user["user_id"]
        )
        user_data = await data_service.users.get_user_by_id(user_id)

        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Return public user data
        return UserPublic(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            roles=user_data.get("roles", []),
            groups=user_data.get("groups", []),
            status=user_data.get("status", "active"),
            created_at=user_data.get("created_at"),
            updated_at=user_data.get("updated_at"),
        )

    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information",
        ) from e


__all__ = ["router"]
