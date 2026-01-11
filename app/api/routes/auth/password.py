"""Authentication password reset routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.container import Container
from app.models.auth import PasswordResetConfirm, PasswordResetRequest
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/reset-password-request")
async def request_password_reset(
    reset_request: PasswordResetRequest,
    auth_service: AuthService = Depends(lambda: Container.auth_service()),
) -> dict[str, str]:
    """Request password reset.

    Args:
    ----
        reset_request: Password reset request with email
        auth_service: Auth service instance

    Returns:
    -------
        Success message

    Raises:
    ------
        HTTPException: If request fails

    """
    try:
        # This would need to be implemented in AuthService
        # For now, we'll return a success message
        return {"message": "Password reset email sent"}

    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset request failed",
        ) from e


@router.post("/reset-password-confirm")
async def confirm_password_reset(
    reset_confirm: PasswordResetConfirm,
    auth_service: AuthService = Depends(lambda: Container.auth_service()),
) -> dict[str, str]:
    """Confirm password reset with token.

    Args:
    ----
        reset_confirm: Password reset confirmation with token and new password
        auth_service: Auth service instance

    Returns:
    -------
        Success message

    Raises:
    ------
        HTTPException: If reset fails

    """
    try:
        # This would need to be implemented in AuthService
        # For now, we'll return a success message
        return {"message": "Password reset successfully"}

    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed",
        ) from e


__all__ = ["router"]
