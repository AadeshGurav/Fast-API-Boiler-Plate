"""Authentication and role-based access control for every non-public route."""

from __future__ import annotations

from dataclasses import replace

from fastapi import HTTPException
from starlette.requests import Request
from starlette.types import Receive, Send

from app.services.audit import AuditActor, audit_actor_var, set_audit_actor
from app.services.error.exceptions import UserFacingExceptionError
from app.utils.utils import client_ip

from .base import BaseMiddleware

METHOD_TO_ACTION = {
    "GET": "read",
    "HEAD": "read",
    "POST": "write",
    "PUT": "write",
    "PATCH": "write",
    "DELETE": "delete",
}


class RBACMiddleware(BaseMiddleware):
    """Authenticates the caller, then checks the permission the route requires.

    Public paths skip everything. Admin-only paths need the ``*`` permission. Every
    other path needs ``<resource>:<action>``, derived from the URL and HTTP method
    (e.g. ``DELETE /api/v1/files/1`` -> ``files:delete``).
    """

    def initialize(self: RBACMiddleware, **kwargs) -> None:
        """Read path lists from config, falling back to the defaults."""
        self.public_paths: list[str] = self.config["public_paths"]
        self.admin_only_paths: list[str] = self.config["admin_only_paths"]
        self.logger.info(
            "RBACMiddleware initialized",
            extra={
                "middleware": "RBACMiddleware",
                "public_paths": self.public_paths,
                "admin_only_paths": self.admin_only_paths,
            },
        )

    async def handle(self, request: Request, receive: Receive, send: Send) -> None:
        """Attribute audit events to the caller, then authenticate and authorize."""
        caller = AuditActor(
            ip_address=client_ip(request), user_agent=request.headers.get("user-agent")
        )
        token = set_audit_actor(caller)
        try:
            await self._authorize(request, receive, send, caller)
        finally:
            audit_actor_var.reset(token)

    async def _authorize(
        self, request: Request, receive: Receive, send: Send, caller: AuditActor
    ) -> None:
        path = request.url.path
        # CORS preflights carry no credentials by design; CORSMiddleware answers them.
        if request.method == "OPTIONS" or self.is_public_path(path):
            await self.app(request.scope, receive, send)
            return

        from app.utils.permissions import authenticate_request

        try:
            user = await authenticate_request(request, request.app.state.services.auth_service)

            required = (
                "*"
                if self.is_admin_only_path(path)
                else self._path_to_permission(path, request.method.upper())
            )
            allowed = await self.rbac_service.check_permission(user.user_id, required)
        except HTTPException as e:
            # Raised before the app runs, so answer directly.
            response = self.error_service.http_response(e, headers=e.headers, instance=path)
            await response(request.scope, receive, send)
            return

        if not allowed:
            self.logger.warning(
                f"Permission denied: user={user.user_id}, permission={required}, path={path}",
                extra={
                    "middleware": "RBACMiddleware",
                    "action": "permission_check",
                    "user_id": user.user_id,
                    "path": path,
                    "method": request.method,
                    "permission": required,
                    "result": "denied",
                },
            )
            response = self.error_service.http_response(
                UserFacingExceptionError(
                    "Admin access required"
                    if required == "*"
                    else f"Permission denied: {required}",
                    status_code=403,
                ),
                instance=path,
            )
            await response(request.scope, receive, send)
            return

        set_audit_actor(replace(caller, user_id=user.user_id))
        await self.app(request.scope, receive, send)

    @staticmethod
    def _path_to_permission(path: str, method: str) -> str:
        """Map a request to the ``resource:action`` permission it requires."""
        for prefix in ("/api/v1/", "/api/"):
            if path.startswith(prefix):
                path = path.removeprefix(prefix)
                break

        resource = path.strip("/").split("/")[0]
        if not resource:
            return "root:read"
        return f"{resource}:{METHOD_TO_ACTION.get(method, 'read')}"
