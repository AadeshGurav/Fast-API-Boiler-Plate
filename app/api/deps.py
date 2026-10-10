"""FastAPI dependencies that hand routes the services of the running application."""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.services.auth import AuthService
from app.services.data import DataService
from app.services.file import FileService
from app.services.oauth import OAuthService
from app.services.rbac import RBACService
from app.services.registry import Services


def get_services(request: Request) -> Services:
    """All services of this application instance."""
    return request.app.state.services


def get_auth_service(request: Request) -> AuthService:
    return get_services(request).auth_service


def get_data_service(request: Request) -> DataService:
    return get_services(request).data_service


def get_file_service(request: Request) -> FileService:
    return get_services(request).file_service


def get_rbac_service(request: Request) -> RBACService:
    return get_services(request).rbac_service


def get_oauth_service(request: Request) -> OAuthService:
    """The OAuth service, or 503 when OAuth is disabled."""
    service = get_services(request).oauth_service
    if service is None or not service.oauth_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OAuth service is not available",
        )
    return service
