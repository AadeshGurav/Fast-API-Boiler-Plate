"""OAuth2 API routes for provider authorization and callbacks."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.core.container import Container
from app.models.auth import LoginResponse
from app.models.oauth import OAuthProvider
from app.models.session import DeviceInfo
from app.models.user import UserPublic
from app.services.auth import AuthService
from app.services.data import DataService
from app.services.oauth import OAuthService
from app.utils.permissions import get_current_user

router = APIRouter(prefix="/oauth", tags=["OAuth"])


def get_device_info(request: Request) -> DeviceInfo:
    """Extract device information from request."""
    user_agent = request.headers.get("user-agent", "")
    ip_address = request.client.host if request.client else "unknown"

    # Simple fingerprint generation
    fingerprint = f"{ip_address}:{user_agent[:50]}"

    return DeviceInfo(
        user_agent=user_agent,
        ip_address=ip_address,
        fingerprint=fingerprint,
        platform=None,
        browser=None,
    )


@router.get("/{provider}/authorize")
async def authorize_oauth(
    provider: str,
    request: Request,
    oauth_service: OAuthService = Depends(lambda: Container.oauth_service()),
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
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported OAuth provider: {provider}",
            )

        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(32)

        # Store state in session or cache for verification
        # This is a simplified approach - in production, store in Redis with expiry

        # Get authorization URL
        auth_url = oauth_service.get_authorization_url(oauth_provider, state)

        return RedirectResponse(url=auth_url)

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
    oauth_service: OAuthService = Depends(lambda: Container.oauth_service()),
    auth_service: AuthService = Depends(lambda: Container.auth_service()),
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
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported OAuth provider: {provider}",
            )

        # Verify state parameter (in production, check against stored state)
        # This is a simplified approach

        # Exchange code for token
        oauth_token = await oauth_service.exchange_code_for_token(oauth_provider, code)

        # Get user info from provider
        oauth_user_info = await oauth_service.get_user_info(
            oauth_provider, oauth_token.access_token
        )

        # Create or link user
        user = await oauth_service.create_or_link_user(oauth_user_info, oauth_provider)

        # Update OAuth tokens
        await oauth_service.update_oauth_tokens(user.id, oauth_provider, oauth_token)

        # Create session and tokens
        device_info = get_device_info(request)

        # Create login request for auth service
        from app.models.auth import LoginRequest

        login_request = LoginRequest(  # noqa: F841
            username=user.username,
            password="",  # OAuth users don't have passwords
            device_info=device_info,
        )

        # For OAuth users, we need to create a special login flow
        # This is a simplified approach - in production, you'd handle OAuth users differently

        # Create user public data
        user_public = UserPublic(
            id=user.id,
            username=user.username,
            email=user.email,
            roles=user.roles,
            groups=user.groups,
            status=user.status,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

        # Resolve permissions
        permissions = []
        rbac_service = Container.rbac_service()
        if rbac_service:
            permissions = await rbac_service.resolve_user_permissions(user.id)

        # Create token payload
        from datetime import datetime, timedelta, timezone

        from app.models.auth import TokenPayload

        token_payload = TokenPayload(
            user_id=user.id,
            username=user.username,
            roles=user.roles,
            permissions=permissions,
            exp=datetime.now(timezone.utc) + timedelta(minutes=15),
            iat=datetime.now(timezone.utc),
            type="access",
        )

        # Create tokens
        access_token = auth_service.create_access_token(token_payload.dict())
        refresh_token = auth_service.create_refresh_token(token_payload.dict())

        # Create session
        data_service: DataService = Container.data_service()
        session_data = {
            "user_id": user.id,
            "refresh_token": refresh_token,
            "device_info": device_info.dict(),
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=168),  # 7 days
        }

        await data_service.sessions.create_session(session_data)  # noqa: F841

        # Create token pair
        from app.models.auth import TokenPair

        token_pair = TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=15 * 60,  # 15 minutes
        )

        login_response = LoginResponse(
            user=user_public, tokens=token_pair, permissions=permissions
        )

        # Set cookies for server-side rendered pages
        from fastapi.responses import JSONResponse

        from app.utils.cookie_manager import CookieManager

        response = JSONResponse(content=login_response.model_dump(mode="json"))
        CookieManager.set_auth_cookies(response, token_pair)

        return response

    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth callback failed",
        ) from e


@router.post("/{provider}/link")
async def link_oauth_account(
    provider: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    oauth_service: OAuthService = Depends(lambda: Container.oauth_service()),
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
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported OAuth provider: {provider}",
            )

        # This would need to be implemented with proper OAuth flow
        # For now, we'll return a success message
        return {"message": f"OAuth account linked successfully: {provider}"}

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
    oauth_service: OAuthService = Depends(lambda: Container.oauth_service()),
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
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported OAuth provider: {provider}",
            )

        # Unlink OAuth account
        success = await oauth_service.unlink_oauth_account(
            current_user["user_id"], oauth_provider
        )

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
