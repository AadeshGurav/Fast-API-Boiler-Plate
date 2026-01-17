"""Authentication login and logout routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer

from app import container as app_container
from app.models.auth import (LoginRequest, LoginResponse, RefreshRequest,
                             TokenPair)
from app.services.auth import AuthService
from app.utils.cookie_manager import CookieManager
from app.utils.permissions import get_current_user
from app.utils.utils import extract_device_info

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
        config: Application configuration

    Returns:
    -------
        Login response with user info and tokens

    Raises:
    ------
        HTTPException: If authentication fails

    """
    try:
        # Extract device info from request
        device_info = extract_device_info(request)

        # Call service with extracted fields
        login_response = await auth_service.login_user(
            username=login_request.username,
            password=login_request.password,
            device_info=device_info,
            remember_me=login_request.remember_me,
        )

        # Set cookies for server-side rendered pages
        response = JSONResponse(content=login_response.model_dump(mode="json"))
        config = getattr(request.app.state, "config", None)
        CookieManager.set_auth_cookies(
            response, login_response.tokens, config, login_request.remember_me
        )
        # Set session cookie
        CookieManager.set_session_cookie(
            response, login_response.session_id, config, login_request.remember_me
        )

        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}",
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
        # Extract device info from request
        device_info = extract_device_info(request)

        # Prefer refresh token from cookie, fallback to body for API clients
        from app.utils.permissions import _extract_refresh_token_from_request

        refresh_token = _extract_refresh_token_from_request(request)
        if not refresh_token:
            refresh_token = refresh_request.refresh_token

        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token required",
            )

        # Call service with extracted fields
        token_pair = await auth_service.refresh_tokens(
            refresh_token=refresh_token,
            device_info=device_info,
        )

        # Detect remember_me from the new refresh token expiry duration
        import jwt

        remember_me = False
        try:
            if token_pair.refresh_token:
                decoded = jwt.decode(
                    token_pair.refresh_token,
                    auth_service.jwt_secret,
                    algorithms=[auth_service.jwt_algorithm],
                    options={"verify_exp": False},
                )
                if decoded.get("exp") and decoded.get("iat"):
                    token_lifetime_seconds = decoded["exp"] - decoded["iat"]
                    # 30 days threshold: 20 * 24 * 60 * 60 = 1728000 seconds
                    remember_me = token_lifetime_seconds > (20 * 24 * 60 * 60)
        except Exception:
            pass  # Default to False if detection fails

        # Set cookies for server-side rendered pages
        response = JSONResponse(content=token_pair.model_dump(mode="json"))
        config = getattr(request.app.state, "config", None)
        CookieManager.set_auth_cookies(response, token_pair, config, remember_me)

        return response

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
        config: Application configuration

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

        success = await auth_service.logout(session_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Logout failed"
            )

        # Clear cookies
        response = JSONResponse(content={"message": "Logged out successfully"})
        CookieManager.delete_auth_cookies(response)
        # Clear session cookie
        config = getattr(request.app.state, "config", None)
        CookieManager.delete_session_cookie(response, config)

        return response

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

        user_id = (
            current_user.user_id
            if hasattr(current_user, "user_id")
            else current_user.get("user_id")
        )
        revoked_count = await auth_service.logout_all_devices(
            user_id, except_session_id=session_id
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
