"""Sign-in with OpenID Connect providers: list them, start, finish, unlink."""

from __future__ import annotations

import secrets

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.deps import get_auth_service, get_oauth_service
from app.models.auth import LoginResponse, TokenPayload
from app.services.auth import AuthService
from app.services.oauth import OAuthService, OIDCError, SignInAttempt, UnknownProviderError
from app.utils.cookie_manager import CookieManager, default_cookie_secure
from app.utils.permissions import get_current_user
from app.utils.utils import extract_device_info

router = APIRouter(prefix="/oauth", tags=["OAuth"])

ATTEMPT_COOKIE_MAX_AGE_SECONDS = 600


def _cookie_name(provider: str) -> str:
    return f"oauth_state_{provider}"


def _unknown(e: UnknownProviderError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/providers", response_model=list[dict[str, str]])
async def list_providers(oauth_service: OAuthService = Depends(get_oauth_service)) -> list[dict]:
    """Configured sign-in providers, for drawing "Sign in with ..." buttons."""
    return oauth_service.describe()


@router.get("/{provider}/authorize", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def authorize_oauth(
    provider: str,
    request: Request,
    oauth_service: OAuthService = Depends(get_oauth_service),
) -> RedirectResponse:
    """Send the browser to the provider (PKCE and nonce included)."""
    try:
        url, attempt = await oauth_service.begin(provider)
    except UnknownProviderError as e:
        raise _unknown(e) from e
    except (OIDCError, httpx.HTTPError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The sign-in provider could not be reached. Try again later.",
        ) from e
    response = RedirectResponse(url=url)
    # The state, PKCE verifier and nonce stay with this browser in an HttpOnly cookie: an
    # attacker cannot make a victim's browser carry values they chose, so a forged callback,
    # a stolen code or a replayed ID token all fail.
    response.set_cookie(
        _cookie_name(provider),
        attempt.pack(),
        max_age=ATTEMPT_COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        secure=default_cookie_secure(request.app.state.services.config),
        samesite="lax",  # must accompany the provider's top-level redirect back
    )
    return response


@router.get("/{provider}/callback", response_model=LoginResponse)
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    request: Request,
    oauth_service: OAuthService = Depends(get_oauth_service),
    auth_service: AuthService = Depends(get_auth_service),
) -> JSONResponse:
    """Finish the sign-in: verify the provider's answer and start a session."""
    attempt = SignInAttempt.unpack(request.cookies.get(_cookie_name(provider)))
    if attempt is None or not secrets.compare_digest(attempt.state, state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state. Start the sign-in again.",
        )
    try:
        user = await oauth_service.complete(provider, code, attempt)
    except UnknownProviderError as e:
        raise _unknown(e) from e
    except (OIDCError, httpx.HTTPError) as e:
        request.app.state.services.logger.warning(f"OAuth sign-in with {provider} refused: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The sign-in provider's answer could not be verified. Start the sign-in again.",
        ) from e
    except ValueError as e:  # no verified email
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e

    login_response = await auth_service.login_oauth_user(user, extract_device_info(request))
    response = JSONResponse(content=login_response.model_dump(mode="json"))
    CookieManager.set_auth_cookies(
        response, login_response.tokens, request.app.state.services.config
    )
    response.delete_cookie(_cookie_name(provider))  # single-use
    return response


@router.post("/{provider}/link", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def link_oauth_account(
    provider: str,
    current_user: TokenPayload = Depends(get_current_user),
    oauth_service: OAuthService = Depends(get_oauth_service),
) -> None:
    """Not supported yet: sign in with the provider using the same verified email."""
    try:
        oauth_service.provider(provider)
    except UnknownProviderError as e:
        raise _unknown(e) from e
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Linking a provider to a signed-in account is not supported yet. "
        "Sign in with the provider using the same verified email to link it.",
    )


@router.delete("/{provider}/unlink")
async def unlink_oauth_account(
    provider: str,
    current_user: TokenPayload = Depends(get_current_user),
    oauth_service: OAuthService = Depends(get_oauth_service),
) -> dict[str, str]:
    """Remove the link between your account and a provider."""
    if not await oauth_service.unlink_oauth_account(current_user.user_id, provider):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such linked provider")
    return {"message": f"OAuth account unlinked successfully: {provider}"}
