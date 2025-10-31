"""Permission utilities and decorators for FastAPI routes."""
from __future__ import annotations

from collections.abc import Callable
from functools import wraps

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer

from app.core.container import Container
from app.core.interfaces.rbac_service_interface import RBACServiceInterface
from app.models.auth import TokenPayload
from app.services.auth import AuthService
from app.services.logger import Logger

# Security scheme for JWT tokens
security = HTTPBearer()


async def get_current_user(
    request: Request,
    token: str = Depends(security),
    auth_service: AuthService = Depends(lambda: Container.auth_service()),
) -> TokenPayload:
    """Get current authenticated user from JWT token.

    Args:
    ----
        request: FastAPI request object
        token: JWT token from Authorization header
        auth_service: Auth service instance

    Returns:
    -------
        Token payload with user information

    Raises:
    ------
        HTTPException: If token is invalid or user not found

    """
    try:
        payload = auth_service.decode_token(token.credentials)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Attach user info to request state for logging
        request.state.user_id = payload.user_id
        request.state.username = payload.username

        return payload

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
            rbac_service: RBACServiceInterface = Container.rbac_service()

            # Check permission
            has_permission = await rbac_service.check_permission(
                current_user.user_id, permission
            )

            if not has_permission:
                # Log denied access
                logger: Logger = Container.logger()
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
                logger: Logger = Container.logger()
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
            rbac_service: RBACServiceInterface = Container.rbac_service()

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
                logger: Logger = Container.logger()
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
                logger: Logger = Container.logger()
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
