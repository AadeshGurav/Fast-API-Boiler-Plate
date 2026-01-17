"""Authentication password reset routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app import container
from app.models.auth import PasswordResetConfirm, PasswordResetRequest
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/reset-password-request")
async def request_password_reset(
    reset_request: PasswordResetRequest,
    auth_service: AuthService = Depends(lambda: container.auth_service()),
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
        result = await auth_service.request_password_reset(reset_request.email)
        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset request failed",
        ) from e


@router.post("/reset-password-confirm")
async def confirm_password_reset(
    reset_confirm: PasswordResetConfirm,
    auth_service: AuthService = Depends(lambda: container.auth_service()),
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
        success = await auth_service.confirm_password_reset(
            reset_confirm.token, reset_confirm.new_password
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset failed",
            )

        return {"message": "Password reset successfully"}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed",
        ) from e


__all__ = ["router"]
