"""Authentication registration route."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_auth_service
from app.models.auth import RegisterRequest
from app.models.user import UserCreate, UserPublic
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(
    registration: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> UserPublic:
    """Create a regular user account.

    Takes ``RegisterRequest`` rather than ``UserCreate``: this endpoint is public, so
    callers must not be able to choose their own roles or groups.
    """
    try:
        return await auth_service.register_user(
            UserCreate(
                username=registration.username,
                email=registration.email,
                password=registration.password,
                roles=[],  # service assigns the default role
                groups=[],
                metadata={
                    "first_name": registration.first_name,
                    "last_name": registration.last_name,
                    "newsletter": registration.newsletter,
                },
            )
        )
    except ValueError as e:
        # Messages come from the service and are written for callers
        # (duplicate username/email, password policy).
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


__all__ = ["router"]
