"""Authentication login, refresh and logout routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.api.deps import get_auth_service
from app.models.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    TokenPair,
    TokenPayload,
)
from app.services.auth import AuthenticationError, AuthService, MFARequiredError
from app.services.error.exceptions import UserFacingExceptionError
from app.utils.cookie_manager import CookieManager
from app.utils.permissions import extract_refresh_token, get_current_user
from app.utils.utils import extract_device_info

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(
    login_request: LoginRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> JSONResponse:
    """Authenticate with username and password and start a session.

    With two-factor authentication on, answers 401 ``mfa_required`` with ``details.mfa_token``
    instead; finish with ``POST /auth/login/mfa``.
    """
    try:
        login_response = await auth_service.login_user(
            username=login_request.username,
            password=login_request.password,
            device_info=extract_device_info(request),
            remember_me=login_request.remember_me,
        )
    except MFARequiredError as e:
        # Not a failure: the client asks for a code and calls POST /auth/login/mfa.
        raise UserFacingExceptionError(
            str(e), code="mfa_required", status_code=401, details={"mfa_token": e.mfa_token}
        ) from e
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    response = JSONResponse(content=login_response.model_dump(mode="json"))
    CookieManager.set_auth_cookies(
        response,
        login_response.tokens,
        request.app.state.services.config,
        login_request.remember_me,
    )
    return response


@router.post("/refresh", response_model=TokenPair)
async def refresh_tokens(
    refresh_request: RefreshRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> JSONResponse:
    """Exchange a refresh token (cookie, else body) for a new token pair."""
    refresh_token = extract_refresh_token(request) or refresh_request.refresh_token
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token_pair = await auth_service.refresh_tokens(
            refresh_token=refresh_token, device_info=extract_device_info(request)
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    remember_me = auth_service.verify_token(token_pair.refresh_token, "refresh").remember_me
    response = JSONResponse(content=token_pair.model_dump(mode="json"))
    CookieManager.set_auth_cookies(
        response, token_pair, request.app.state.services.config, remember_me
    )
    return response


@router.post("/logout")
async def logout(
    request: Request,
    current_user: TokenPayload = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> JSONResponse:
    """End the current session; its access and refresh tokens stop working."""
    if not current_user.sid or not await auth_service.logout(current_user.sid):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No active session to end"
        )

    response = JSONResponse(content={"message": "Logged out successfully"})
    CookieManager.delete_auth_cookies(response, request.app.state.services.config)
    return response


@router.post("/logout-all")
async def logout_all_devices(
    current_user: TokenPayload = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, int | str]:
    """End every session of the current user except the one making this request."""
    revoked_count = await auth_service.logout_all_devices(
        current_user.user_id, except_session_id=current_user.sid
    )
    return {
        "message": "Logged out from all other devices",
        "revoked_sessions": revoked_count,
    }


__all__ = ["router"]
