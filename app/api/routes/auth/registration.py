"""Authentication registration routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app import container as app_container
from app.models.user import UserCreate, UserPublic
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED
)
async def register(
    user_data: UserCreate,
    request: Request,
    auth_service: AuthService = Depends(lambda: app_container.auth_service()),
) -> UserPublic:
    """Register a new user.

    Args:
    ----
        user_data: User registration data
        request: FastAPI request object
        auth_service: Auth service instance

    Returns:
    -------
        Created user information

    Raises:
    ------
        HTTPException: If registration fails

    """
    try:
        user = await auth_service.register_user(user_data)

        # Return public user data
        return UserPublic(
            id=user.id,
            username=user.username,
            email=user.email,
            roles=user.roles,
            groups=user.groups,
            status=user.status,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        ) from e


__all__ = ["router"]
