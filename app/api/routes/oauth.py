"""OAuth2 API routes for provider authorization and callbacks."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.deps import get_auth_service, get_oauth_service
from app.models.oauth import OAuthProvider
from app.services.auth import AuthService
from app.services.oauth import OAuthService
from app.utils.cookie_manager import CookieManager
from app.utils.permissions import get_current_user
from app.utils.utils import extract_device_info

router = APIRouter(prefix="/oauth", tags=["OAuth"])

STATE_COOKIE_MAX_AGE_SECONDS = 600


def _state_cookie_name(provider: str) -> str:
    return f"oauth_state_{provider}"


@router.get("/{provider}/authorize")
async def authorize_oauth(
    provider: str,
    request: Request,
    oauth_service: OAuthService = Depends(get_oauth_service),
):
    """Initiate OAuth authorization flow.

    Args:
    ----
        provider: OAuth provider name
        request: FastAPI request object
        oauth_service: OAuth service instance

    Returns:
    -------
        Redirect to OAuth provider

    Raises:
    ------
        HTTPException: If provider is not supported

    """
    try:
        # Validate provider
        try:
            oauth_provider = OAuthProvider(provider)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported OAuth provider: {provider}",
            ) from e

        # CSRF protection: bind the state to this browser with an HttpOnly cookie and
        # compare it in the callback. An attacker can't make a victim's browser
        # carry a cookie they chose, so a forged callback fails the comparison.
        state = secrets.token_urlsafe(32)
        auth_url = oauth_service.get_authorization_url(oauth_provider, state)

        response = RedirectResponse(url=auth_url)
        from app.utils.cookie_manager import default_cookie_secure

        config = request.app.state.services.config
        response.set_cookie(
            _state_cookie_name(provider),
            state,
            max_age=STATE_COOKIE_MAX_AGE_SECONDS,
            httponly=True,
            secure=default_cookie_secure(config),
            samesite="lax",  # must accompany the provider's top-level redirect back
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth authorization failed",
        ) from e


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    request: Request,
    oauth_service: OAuthService = Depends(get_oauth_service),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Handle OAuth callback and complete authentication.

    Args:
    ----
        provider: OAuth provider name
        code: Authorization code from provider
        state: State parameter for CSRF protection
        request: FastAPI request object
        oauth_service: OAuth service instance
        auth_service: Auth service instance

    Returns:
    -------
        Login response with user info and tokens

    Raises:
    ------
        HTTPException: If OAuth flow fails

    """
    try:
        # Validate provider
        try:
            oauth_provider = OAuthProvider(provider)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported OAuth provider: {provider}",
            ) from e

        expected_state = request.cookies.get(_state_cookie_name(provider))
        if not expected_state or not secrets.compare_digest(expected_state, state):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OAuth state. Start the sign-in again.",
            )

        # Exchange code for token
        oauth_token = await oauth_service.exchange_code_for_token(oauth_provider, code)

        # Get user info from provider
        oauth_user_info = await oauth_service.get_user_info(
            oauth_provider, oauth_token.access_token
        )

        # Create or link user
        user = await oauth_service.create_or_link_user(oauth_user_info, oauth_provider)

        # Same session/token machinery as password login
        login_response = await auth_service.login_oauth_user(user, extract_device_info(request))

        response = JSONResponse(content=login_response.model_dump(mode="json"))
        CookieManager.set_auth_cookies(
            response, login_response.tokens, request.app.state.services.config
        )
        response.delete_cookie(_state_cookie_name(provider))  # state is single-use
        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth callback failed",
        ) from e


@router.post("/{provider}/link")
async def link_oauth_account(
    provider: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    oauth_service: OAuthService = Depends(get_oauth_service),
):
    """Link OAuth account to current user.

    Args:
    ----
        provider: OAuth provider name
        request: FastAPI request object
        current_user: Current authenticated user
        oauth_service: OAuth service instance

    Returns:
    -------
        Success message

    Raises:
    ------
        HTTPException: If linking fails

    """
    try:
        # Validate provider
        try:
            oauth_provider = OAuthProvider(provider)  # noqa: F841
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported OAuth provider: {provider}",
            ) from e

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Linking a provider to a signed-in account is not supported yet. "
            "Sign in with the provider using the same verified email to link it.",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth account linking failed",
        ) from e


@router.delete("/{provider}/unlink")
async def unlink_oauth_account(
    provider: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    oauth_service: OAuthService = Depends(get_oauth_service),
):
    """Unlink OAuth account from current user.

    Args:
    ----
        provider: OAuth provider name
        request: FastAPI request object
        current_user: Current authenticated user
        oauth_service: OAuth service instance

    Returns:
    -------
        Success message

    Raises:
    ------
        HTTPException: If unlinking fails

    """
    try:
        # Validate provider
        try:
            oauth_provider = OAuthProvider(provider)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported OAuth provider: {provider}",
            ) from e

        # Unlink OAuth account
        success = await oauth_service.unlink_oauth_account(current_user.user_id, oauth_provider)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to unlink OAuth account",
            )

        return {"message": f"OAuth account unlinked successfully: {provider}"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth account unlinking failed",
        ) from e
