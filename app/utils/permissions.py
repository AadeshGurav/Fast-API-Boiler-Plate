"""Permission utilities and decorators for FastAPI routes."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import container
from app.core.interfaces.rbac_service_interface import RBACServiceInterface
from app.models.auth import TokenPayload
from app.services.auth import AuthService
from app.services.logger import Logger
from config import Config

# Security scheme for JWT tokens
security = HTTPBearer()


def get_token_cookie_names() -> tuple[str, str]:
    """Get access and refresh token cookie names from config.

    Returns
    -------
        Tuple of (access_token_key, refresh_token_key)

    """
    config: Config = container.config()
    app_title = config.get("app_title", "app")
    app_title_safe = app_title.lower().replace(" ", "_")
    access_token_key = f"{app_title_safe}_access_token"
    refresh_token_key = f"{app_title_safe}_refresh_token"
    return access_token_key, refresh_token_key


def get_auth_service() -> AuthService:
    """Dependency function to get AuthService instance.

    Returns
    -------
        AuthService instance from container

    """
    return container.auth_service()


def _extract_token_from_request(request: Request) -> str | None:
    """Extract token from request cookies or Authorization header.

    Args:
    ----
        request: FastAPI request object

    Returns:
    -------
        Token string or None if not found

    """
    access_token_key, _ = get_token_cookie_names()
    token = request.cookies.get(access_token_key) or request.cookies.get("auth_token")
    if token:
        return token

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.removeprefix("Bearer ").strip()

    return None


def _extract_refresh_token_from_request(request: Request) -> str | None:
    """Extract refresh token from request cookies.

    Args:
    ----
        request: FastAPI request object

    Returns:
    -------
        Refresh token string or None if not found

    """
    _, refresh_token_key = get_token_cookie_names()
    return request.cookies.get(refresh_token_key)


async def _attempt_token_refresh(
    request: Request, auth_service: AuthService
) -> TokenPayload | None:
    """Attempt to refresh expired access token using refresh token.

    Args:
    ----
        request: FastAPI request object
        auth_service: Auth service instance

    Returns:
    -------
        New token payload if refresh successful, None otherwise

    """
    from app.utils.utils import extract_device_info

    try:
        refresh_token = _extract_refresh_token_from_request(request)
        if not refresh_token:
            return None

        device_info = extract_device_info(request)
        token_pair = await auth_service.refresh_tokens(refresh_token, device_info)

        if not token_pair or not token_pair.access_token:
            return None

        payload = auth_service.verify_token(token_pair.access_token, "access")
        if not payload:
            return None

        request.state.token_refreshed = True
        request.state.new_access_token = token_pair.access_token
        request.state.new_refresh_token = token_pair.refresh_token
        request.state.token_expires_in = token_pair.expires_in

        # Check if new refresh token is a 30-day token (remember_me was preserved)
        # This is detected by checking the token expiry duration
        import jwt

        try:
            decoded = jwt.decode(
                token_pair.refresh_token,
                auth_service.jwt_secret,
                algorithms=[auth_service.jwt_algorithm],
                options={"verify_exp": False},
            )
            if decoded.get("exp") and decoded.get("iat"):
                # exp and iat are timestamps (seconds since epoch)
                token_lifetime_seconds = decoded["exp"] - decoded["iat"]
                # 30 days = 30 * 24 * 60 * 60 = 2592000 seconds
                # Default is 7 days = 7 * 24 * 60 * 60 = 604800 seconds
                # Use 20 days as threshold: 20 * 24 * 60 * 60 = 1728000 seconds
                remember_me = token_lifetime_seconds > (20 * 24 * 60 * 60)
                request.state.remember_me = remember_me
            else:
                request.state.remember_me = False
        except Exception:
            request.state.remember_me = False

        return payload

    except Exception:
        return None


async def get_current_user(
    request: Request,
    token: HTTPAuthorizationCredentials | None = Depends(security),
    auth_service: AuthService | None = Depends(get_auth_service),
) -> TokenPayload:
    """Get current authenticated user from JWT token with automatic refresh.

    Automatically attempts to refresh expired access tokens using refresh token
    from cookies. Works both as a FastAPI dependency and when called directly.

    Args:
    ----
        request: FastAPI request object
        token: HTTPAuthorizationCredentials from Authorization header (when used as dependency)
        auth_service: Auth service instance (when used as dependency)

    Returns:
    -------
        Token payload with user information

    Raises:
    ------
        HTTPException: If token is invalid or user not found

    """
    try:
        # Handle direct calls (not as dependency) - extract token and auth_service manually
        # When called directly, token will be a Depends object, not HTTPAuthorizationCredentials
        if not isinstance(token, HTTPAuthorizationCredentials):
            token_str = _extract_token_from_request(request)
            if not token_str:
                # If no access token, try to refresh using refresh token before failing
                # This handles the case where access token cookie expired but refresh token still exists
                # When called directly, auth_service will be a Depends object, not AuthService
                if not isinstance(auth_service, AuthService):
                    auth_service = container.auth_service()

                # Try to refresh using refresh token
                refreshed_payload = await _attempt_token_refresh(request, auth_service)
                if refreshed_payload:
                    # Attach user info to request state for logging
                    request.state.user_id = refreshed_payload.user_id
                    request.state.username = refreshed_payload.username
                    return refreshed_payload

                # Log available cookies for debugging
                if hasattr(request, "cookies") and request.cookies:
                    cookie_names = list(request.cookies.keys())
                    logger = container.logger()
                    logger.debug(
                        "No token found in request",
                        extra={
                            "available_cookies": cookie_names,
                            "path": request.url.path,
                        },
                    )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            token_credentials = token_str
        else:
            token_credentials = token.credentials

        # When called directly, auth_service will be a Depends object, not AuthService
        if not isinstance(auth_service, AuthService):
            auth_service = container.auth_service()

        payload = auth_service.verify_token(token_credentials, "access")

        if not payload:
            from datetime import datetime, timezone

            import jwt

            token_expired = False
            exp_datetime = None
            try:
                decoded = jwt.decode(
                    token_credentials,
                    auth_service.jwt_secret,
                    algorithms=[auth_service.jwt_algorithm],
                    options={"verify_signature": False, "verify_exp": False},
                )
                exp_timestamp = decoded.get("exp")
                if exp_timestamp:
                    exp_datetime = datetime.fromtimestamp(
                        exp_timestamp, tz=timezone.utc
                    )
                    now = datetime.now(timezone.utc)
                    if exp_datetime < now:
                        token_expired = True
            except jwt.ExpiredSignatureError:
                token_expired = True
            except Exception:
                pass

            if token_expired:
                refreshed_payload = await _attempt_token_refresh(request, auth_service)
                if refreshed_payload:
                    payload = refreshed_payload
                else:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token expired and refresh failed",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        # Attach user info to request state for logging
        request.state.user_id = payload.user_id
        request.state.username = payload.username

        return payload

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def require_permission(permission: str):
    """Decorator to require specific permission for route access.

    Args:
    ----
        permission: Required permission string

    Returns:
    -------
        Decorated function

    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request and current user from kwargs
            request = kwargs.get("request")
            current_user = kwargs.get("current_user")

            if not request or not current_user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Permission check failed: missing request or user context",
                )

            # Get RBAC service
            rbac_service: RBACServiceInterface = container.rbac_service()

            # Check permission
            has_permission = await rbac_service.check_permission(
                current_user.user_id, permission
            )

            if not has_permission:
                # Log denied access
                logger: Logger = container.logger()
                logger.warning(
                    f"Permission denied: user={current_user.user_id}, permission={permission}, path={request.url.path}",
                    extra={
                        "service": "permissions",
                        "action": "permission_check",
                        "user_id": current_user.user_id,
                        "permission": permission,
                        "path": request.url.path,
                        "method": request.method,
                        "result": "denied",
                    },
                )

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_role(role: str):
    """Decorator to require specific role for route access.

    Args:
    ----
        role: Required role string

    Returns:
    -------
        Decorated function

    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request and current user from kwargs
            request = kwargs.get("request")
            current_user = kwargs.get("current_user")

            if not request or not current_user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Role check failed: missing request or user context",
                )

            # Check if user has the required role
            if role not in current_user.roles:
                # Log denied access
                logger: Logger = container.logger()
                logger.warning(
                    f"Role access denied: user={current_user.user_id}, role={role}, path={request.url.path}",
                    extra={
                        "service": "permissions",
                        "action": "role_check",
                        "user_id": current_user.user_id,
                        "role": role,
                        "path": request.url.path,
                        "method": request.method,
                        "result": "denied",
                    },
                )

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role required: {role}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_any_permission(permissions: list[str]):
    """Decorator to require any of the specified permissions for route access.

    Args:
    ----
        permissions: List of permission strings (user needs at least one)

    Returns:
    -------
        Decorated function

    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request and current user from kwargs
            request = kwargs.get("request")
            current_user = kwargs.get("current_user")

            if not request or not current_user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Permission check failed: missing request or user context",
                )

            # Get RBAC service
            rbac_service: RBACServiceInterface = container.rbac_service()

            # Check if user has any of the required permissions
            has_any_permission = False
            for permission in permissions:
                if await rbac_service.check_permission(
                    current_user.user_id, permission
                ):
                    has_any_permission = True
                    break

            if not has_any_permission:
                # Log denied access
                logger: Logger = container.logger()
                logger.warning(
                    f"Permission denied: user={current_user.user_id}, permissions={permissions}, path={request.url.path}",  # noqa: E501
                    extra={
                        "service": "permissions",
                        "action": "any_permission_check",
                        "user_id": current_user.user_id,
                        "permissions": permissions,
                        "path": request.url.path,
                        "method": request.method,
                        "result": "denied",
                    },
                )

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: requires one of {permissions}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_admin():
    """Decorator to require admin role for route access.

    Returns
    -------
        Decorated function

    """
    return require_role("admin")


def require_manager_or_admin():
    """Decorator to require manager or admin role for route access.

    Returns
    -------
        Decorated function

    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request and current user from kwargs
            request = kwargs.get("request")
            current_user = kwargs.get("current_user")

            if not request or not current_user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Role check failed: missing request or user context",
                )

            # Check if user has manager or admin role
            if not any(role in current_user.roles for role in ["admin", "manager"]):
                # Log denied access
                logger: Logger = container.logger()
                logger.warning(
                    f"Role access denied: user={current_user.user_id}, required=manager_or_admin, path={request.url.path}",  # noqa: E501
                    extra={
                        "service": "permissions",
                        "action": "manager_or_admin_check",
                        "user_id": current_user.user_id,
                        "path": request.url.path,
                        "method": request.method,
                        "result": "denied",
                    },
                )

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Role required: manager or admin",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# FastAPI dependencies for common permission checks
RequireAdmin = Depends(lambda: require_admin())
RequireManagerOrAdmin = Depends(lambda: require_manager_or_admin())
RequireUserRead = Depends(lambda: require_permission("users:read"))
RequireUserWrite = Depends(lambda: require_permission("users:write"))
RequireProfileRead = Depends(lambda: require_permission("profile:read"))
RequireProfileWrite = Depends(lambda: require_permission("profile:write"))


__all__ = [
    "get_current_user",
    "require_permission",
    "require_role",
    "require_any_permission",
    "require_admin",
    "require_manager_or_admin",
    "RequireAdmin",
    "RequireManagerOrAdmin",
    "RequireUserRead",
    "RequireUserWrite",
    "RequireProfileRead",
    "RequireProfileWrite",
]
