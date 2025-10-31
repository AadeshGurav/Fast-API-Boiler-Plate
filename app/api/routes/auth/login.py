"""Authentication login and logout routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer

from app import container as app_container
from app.models.auth import LoginRequest, LoginResponse, RefreshRequest, TokenPair
from app.services.auth import AuthService
from app.utils.permissions import get_current_user
from app.utils.uitls import extract_device_info

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


@router.post("/login", response_model=LoginResponse)
async def login(
    login_request: LoginRequest,
    request: Request,
    auth_service: AuthService = Depends(lambda: app_container.auth_service()),
) -> LoginResponse:
    """Authenticate user and create session.

    Args:
    ----
        login_request: Login credentials and device info
        request: FastAPI request object
        auth_service: Auth service instance

    Returns:
    -------
        Login response with user info and tokens

    Raises:
    ------
        HTTPException: If authentication fails

    """
    try:
        # Add device info to login request
        device_info = extract_device_info(request)
        login_request.device_info = device_info

        login_response = await auth_service.login_user(login_request)
        return login_response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed"
        ) from e


@router.post("/refresh", response_model=TokenPair)
async def refresh_tokens(
    refresh_request: RefreshRequest,
    request: Request,
    auth_service: AuthService = Depends(lambda: app_container.auth_service()),
) -> TokenPair:
    """Refresh access token using refresh token.

    Args:
    ----
        refresh_request: Refresh token and device info
        request: FastAPI request object
        auth_service: Auth service instance

    Returns:
    -------
        New token pair

    Raises:
    ------
        HTTPException: If token refresh fails

    """
    try:
        # Add device info to refresh request
        device_info = extract_device_info(request)
        refresh_request.device_info = device_info

        token_pair = await auth_service.refresh_tokens(refresh_request)
        return token_pair

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        ) from e


@router.post("/logout")
async def logout(
    request: Request,
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(lambda: app_container.auth_service()),
) -> dict[str, str]:
    """Logout user by revoking current session.

    Args:
    ----
        request: FastAPI request object
        current_user: Current authenticated user
        auth_service: Auth service instance

    Returns:
    -------
        Success message

    Raises:
    ------
        HTTPException: If logout fails

    """
    try:
        # Extract session ID from request (this would need to be implemented)
        # For now, we'll use a placeholder
        session_id = getattr(request.state, "session_id", None)

        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Session ID not found"
            )

        success = await auth_service.logout_user(session_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Logout failed"
            )

        return {"message": "Logged out successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logout failed"
        ) from e


@router.post("/logout-all")
async def logout_all_devices(
    request: Request,
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(lambda: app_container.auth_service()),
) -> dict[str, int | str]:
    """Logout user from all devices.

    Args:
    ----
        request: FastAPI request object
        current_user: Current authenticated user
        auth_service: Auth service instance

    Returns:
    -------
        Success message with count of revoked sessions

    Raises:
    ------
        HTTPException: If logout fails

    """
    try:
        # Extract session ID from request (this would need to be implemented)
        session_id = getattr(request.state, "session_id", None)

        revoked_count = await auth_service.logout_all_devices(
            current_user["user_id"], except_session_id=session_id
        )

        return {
            "message": "Logged out from all devices",
            "revoked_sessions": revoked_count,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logout failed"
        ) from e


__all__ = ["router"]
