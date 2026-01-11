from __future__ import annotations

from collections.abc import Callable

from fastapi import Request, Response
from starlette.datastructures import MutableHeaders

from app.services.error.exceptions import UserFacingExceptionError
from app.services.logger import create_log_context

from .base import BaseMiddleware


class RBACMiddleware(BaseMiddleware):
    """Enhanced Role-Based Access Control (RBAC) middleware using RBAC service."""

    def initialize(
        self: RBACMiddleware,
        **kwargs,
    ) -> None:
        """Initialize RBAC middleware with RBAC service.

        Args:
        ----
            kwargs: Additional keyword arguments.

        """
        self.public_paths: list[str] = self.config.get(
            "public_paths",
            [
                "/",
                "/login",
                "/health",
                "/docs",
                "/redoc",
                "/openapi.json",
                "/api/v1/auth/register",
                "/api/v1/auth/login",
                "/api/v1/auth/refresh",
                "/api/v1/oauth/google/authorize",
                "/api/v1/oauth/google/callback",
                "/api/v1/oauth/apple/authorize",
                "/api/v1/oauth/apple/callback",
            ],
        )
        self.admin_only_paths: list[str] = self.config.get(
            "admin_only_paths", ["/api/v1/rbac", "/api/v1/admin"]
        )

        self.logger.info(
            "Enhanced RBACMiddleware initialized",
            extra={
                "middleware": "RBACMiddleware",
                "public_paths": self.public_paths,
                "admin_only_paths": self.admin_only_paths,
                "rbac_service_available": self.rbac_service is not None,
            },
        )

    async def process_request(
        self: RBACMiddleware, request: Request, call_next: Callable
    ) -> Response:
        """Main request processing pipeline for RBAC checks using RBAC service.

        Args:
        ----
            request: The request to process.
            call_next: The next middleware to call.

        Returns:
        -------
            The response from the next middleware.

        """
        path = request.url.path
        method = request.method.upper()

        # Allow public paths
        if self.is_public_path(path):
            self.logger.debug(f"Public path allowed: {path}")
            return await call_next(request)

        # Get token
        token = self._get_token_from_request(request)
        if not token:
            self.logger.warning(
                f"Authentication required: {path}",
                extra={
                    "middleware": "RBACMiddleware",
                    "action": "auth_required",
                    "path": path,
                    "method": method,
                },
            )

            return self.error_service.http_response(
                UserFacingExceptionError("Authentication required", status_code=401),
                status_code=401,
            )

        try:
            # Decode token via DI container
            from app.core.container import Container

            auth_service = Container.auth_service()
            user_data = auth_service.decode_token(token, verify_type="access")
            user_id = user_data.get("user_id")
            username = user_data.get("username")
            roles = user_data.get("roles", [])

            # Check admin-only paths
            if self.is_admin_only_path(path):
                has_admin_permission = (
                    await self.rbac_service.check_permission(user_id, "*")
                    if self.rbac_service
                    else "admin" in roles
                )
                if not has_admin_permission:
                    self.logger.warning(
                        f"Admin access denied: user={username}, path={path}",
                        extra={
                            "middleware": "RBACMiddleware",
                            "action": "admin_check",
                            "user_id": user_id,
                            "username": username,
                            "path": path,
                            "method": method,
                            "roles": roles,
                            "result": "denied",
                        },
                    )

                    return self.error_service.http_response(
                        UserFacingExceptionError(
                            "Admin access required", status_code=403
                        ),
                        status_code=403,
                    )

            # Check specific permissions for the path
            if self.rbac_service:
                # Convert path to permission format (e.g., /api/v1/users -> users:read)
                permission = self._path_to_permission(path, method)
                has_permission = await self.rbac_service.check_permission(
                    user_id, permission
                )
                if not has_permission:
                    self.logger.warning(
                        f"Permission denied: user={username}, permission={permission}, path={path}",
                        extra=create_log_context(
                            middleware="RBACMiddleware",
                            action="permission_check",
                            user_id=user_id,
                            username=username,
                            path=path,
                            method=method,
                            permission=permission,
                            roles=roles,
                            result="denied",
                        ),
                    )

                    return self.error_service.http_response(
                        UserFacingExceptionError(
                            f"Permission denied: {permission}",
                            status_code=403,
                        ),
                        status_code=403,
                    )

            # Store user context
            request.state.user = user_data
            request.state.user_id = user_id
            request.state.username = username
            request.state.user_role = roles[0] if roles else None

            # Add trace headers
            headers = MutableHeaders(request.headers)
            headers["X-User-Role"] = str(roles[0] if roles else "")
            headers["X-User-ID"] = str(user_id or "")

            # Log successful access
            self.logger.debug(
                f"Access granted: user={username}, path={path}",
                extra={
                    "middleware": "RBACMiddleware",
                    "action": "access_granted",
                    "user_id": user_id,
                    "username": username,
                    "path": path,
                    "method": method,
                    "roles": roles,
                },
            )

            # Continue pipeline
            response = await call_next(request)
            response.headers["X-User-Role"] = str(roles[0] if roles else "")
            return response

        except Exception as e:  # noqa: BLE001
            self.logger.error(
                f"Authentication failed: {str(e)}, path={path}",
                extra={
                    "middleware": "RBACMiddleware",
                    "action": "auth_failed",
                    "path": path,
                    "method": method,
                    "error": str(e),
                },
            )

            return self.error_service.http_response(
                UserFacingExceptionError(
                    f"Authentication failed: {str(e)}", status_code=401
                ),
                status_code=401,
            )

    # --------------------------
    # Helpers
    # --------------------------

    def _get_token_from_request(self: RBACMiddleware, request: Request) -> str | None:
        """Extract token from cookie or Authorization header.

        Args:
        ----
            request: The request to process.

        Returns:
        -------
            The token from the request.

        """
        from app.utils.permissions import get_token_cookie_names

        access_token_key, _ = get_token_cookie_names()
        token = request.cookies.get(access_token_key) or request.cookies.get(
            "auth_token"
        )
        if token:
            return token

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header.removeprefix("Bearer ").strip()

        return None

    def is_public_path(self: RBACMiddleware, path: str) -> bool:
        """Check if path is public.

        Args:
        ----
            path: The path to check.

        Returns:
        -------
            True if path is public, False otherwise.

        """
        return any(path.startswith(p) for p in self.public_paths)

    def is_admin_only_path(self: RBACMiddleware, path: str) -> bool:
        """Check if path is restricted to admin.

        Args:
        ----
            path: The path to check.

        Returns:
        -------
            True if path is restricted to admin, False otherwise.

        """
        return any(path.startswith(p) for p in self.admin_only_paths)

    def _path_to_permission(self: RBACMiddleware, path: str, method: str) -> str:
        """Convert API path and method to permission format.

        Args:
        ----
            path: The API path.
            method: The HTTP method.

        Returns:
        -------
            Permission string in format "resource:action".

        """
        # Remove API version prefix
        if path.startswith("/api/v1/"):
            path = path[8:]
        elif path.startswith("/api/"):
            path = path[5:]

        # Extract resource from path
        parts = path.strip("/").split("/")
        if not parts or parts[0] == "":
            return "root:read"

        resource = parts[0]

        # Map HTTP methods to actions
        method_to_action = {
            "GET": "read",
            "POST": "write",
            "PUT": "write",
            "PATCH": "write",
            "DELETE": "delete",
        }

        action = method_to_action.get(method, "read")

        return f"{resource}:{action}"
