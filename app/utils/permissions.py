"""Authentication and authorization dependencies for FastAPI routes.

``authenticate_request`` is the single place that turns a request into a verified
``TokenPayload``; both the RBAC middleware and the ``get_current_user`` dependency use
it, so a request is verified once.

Authorization is expressed as dependencies::

    @router.get("/reports", dependencies=[Depends(require_permission("reports:read"))])
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import get_auth_service, get_data_service, get_rbac_service, get_services
from app.models.auth import TokenPair, TokenPayload
from app.services.auth import AuthenticationError, AuthService
from app.services.auth.api_tokens import is_api_token
from app.services.sentry import set_user as set_sentry_user
from app.utils.cookie_manager import get_token_cookie_names

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from app.services.data import DataService
    from app.services.rbac import RBACService
    from app.services.registry import Services

# auto_error=False: browsers authenticate with HttpOnly cookies, not a header, so a
# missing Authorization header must fall through to the cookie instead of failing.
security = HTTPBearer(auto_error=False)

_UNAUTHENTICATED = {"WWW-Authenticate": "Bearer"}


def extract_access_token(request: Request) -> str | None:
    """Access token from the Authorization header, else from the auth cookie."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.removeprefix("Bearer ").strip() or None

    access_token_key, _ = get_token_cookie_names(request.app.state.services.config)
    return request.cookies.get(access_token_key)


def extract_refresh_token(request: Request) -> str | None:
    """Refresh token from its cookie."""
    _, refresh_token_key = get_token_cookie_names(request.app.state.services.config)
    return request.cookies.get(refresh_token_key)


async def _silent_refresh(request: Request, auth_service: AuthService) -> TokenPayload | None:
    """Trade the refresh-token cookie for a new pair when the access token is gone.

    The new pair is parked on ``request.state`` so SessionMiddleware can write the
    cookies onto the response.
    """
    from app.utils.utils import extract_device_info

    refresh_token = extract_refresh_token(request)
    if not refresh_token:
        return None

    try:
        token_pair: TokenPair = await auth_service.refresh_tokens(
            refresh_token, extract_device_info(request)
        )
    except AuthenticationError:
        return None

    payload = auth_service.verify_token(token_pair.access_token, "access")
    refreshed = auth_service.verify_token(token_pair.refresh_token, "refresh")
    if not payload or not refreshed:
        return None

    request.state.new_tokens = token_pair
    request.state.remember_me = refreshed.remember_me
    return payload


async def authenticate_request(
    request: Request,
    auth_service: AuthService,
    credentials: HTTPAuthorizationCredentials | None = None,
) -> TokenPayload:
    """Verify the request's credentials and return the token claims.

    A token is accepted only if it is validly signed, unexpired, an access token,
    and its session is still active (logout/revocation takes effect immediately).
    If there is no usable access token but a valid refresh cookie, the session is
    refreshed transparently.

    Raises:
    ------
        HTTPException: 401 if the request cannot be authenticated.

    """
    cached = getattr(request.state, "auth", None)
    if cached is not None:
        return cached

    token = credentials.credentials if credentials else extract_access_token(request)
    if is_api_token(token):
        # Personal access tokens are stateless for the caller: no session, no silent refresh.
        payload = await auth_service.api_tokens.authenticate(token)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API token",
                headers=_UNAUTHENTICATED,
            )
        return _remember(request, payload)
    payload = auth_service.verify_token(token, "access") if token else None
    if payload and not await auth_service.is_session_active(payload.sid):
        payload = None
    if payload is None:
        payload = await _silent_refresh(request, auth_service)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers=_UNAUTHENTICATED,
        )

    return _remember(request, payload)


def _remember(request: Request, payload: TokenPayload) -> TokenPayload:
    """Keep the verified caller on the request so later checks do not verify again."""
    request.state.auth = payload
    set_sentry_user(payload.user_id, payload.username)
    request.state.user_id = payload.user_id
    request.state.username = payload.username
    request.state.session_id = payload.sid
    return payload


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenPayload:
    """FastAPI dependency: the authenticated user's token claims (401 otherwise)."""
    return await authenticate_request(request, auth_service, credentials)


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


async def get_session_user(user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
    """Like ``get_current_user``, but refuses API tokens: for actions a token must never take
    on its own behalf, such as minting more tokens."""
    if user.scopes is not None:
        raise _forbidden("Sign in with your password to do this; API tokens cannot")
    return user


def require_permission(permission: str) -> Callable[..., Awaitable[TokenPayload]]:
    """Dependency factory: the user must hold ``permission`` (``*`` satisfies any)."""

    async def dependency(
        user: TokenPayload = Depends(get_current_user),
        rbac: RBACService = Depends(get_rbac_service),
        services: Services = Depends(get_services),
    ) -> TokenPayload:
        if not await rbac.allows(user, permission):
            _log_denied(services, user, f"permission {permission}")
            raise _forbidden(f"Permission denied: {permission}")
        return user

    return dependency


def require_any_permission(
    permissions: list[str],
) -> Callable[..., Awaitable[TokenPayload]]:
    """Dependency factory: the user must hold at least one of ``permissions``."""

    async def dependency(
        user: TokenPayload = Depends(get_current_user),
        rbac: RBACService = Depends(get_rbac_service),
        services: Services = Depends(get_services),
    ) -> TokenPayload:
        for permission in permissions:
            if await rbac.allows(user, permission):
                return user
        _log_denied(services, user, f"any of {permissions}")
        raise _forbidden(f"Permission denied: requires one of {permissions}")

    return dependency


def require_any_role(roles: list[str]) -> Callable[..., Awaitable[TokenPayload]]:
    """Dependency factory: the user must currently hold one of ``roles``.

    Roles are read from the user record, not the token, so removing a role takes
    effect immediately instead of when the access token expires.
    """

    async def dependency(
        user: TokenPayload = Depends(get_current_user),
        data: DataService = Depends(get_data_service),
        services: Services = Depends(get_services),
    ) -> TokenPayload:
        record = await data.users.get_user_by_id(user.user_id)
        if not record or not set(roles) & set(record.get("roles", [])):
            _log_denied(services, user, f"role {roles}")
            raise _forbidden(f"Role required: {' or '.join(roles)}")
        return user

    return dependency


def require_role(role: str) -> Callable[..., Awaitable[TokenPayload]]:
    """Dependency factory: the user must currently hold ``role``."""
    return require_any_role([role])


def require_admin() -> Callable[..., Awaitable[TokenPayload]]:
    """Dependency factory: the user must be an administrator."""
    return require_role("admin")


def require_manager_or_admin() -> Callable[..., Awaitable[TokenPayload]]:
    """Dependency factory: the user must be a manager or an administrator."""
    return require_any_role(["admin", "manager"])


def _log_denied(services: Services, user: TokenPayload, requirement: str) -> None:
    services.logger.warning(
        f"Access denied: user={user.user_id}, requires {requirement}",
        extra={
            "service": "permissions",
            "action": "access_denied",
            "user_id": user.user_id,
            "requirement": requirement,
        },
    )


__all__ = [
    "authenticate_request",
    "extract_access_token",
    "extract_refresh_token",
    "get_auth_service",
    "get_current_user",
    "get_session_user",
    "require_admin",
    "require_any_permission",
    "require_any_role",
    "require_manager_or_admin",
    "require_permission",
    "require_role",
    "security",
]
