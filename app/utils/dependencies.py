"""FastAPI dependency functions for hot-pluggable services.

These dependencies automatically check if services are enabled before returning them.
If a service is disabled, an appropriate HTTPException is raised.
"""

from __future__ import annotations

from fastapi import HTTPException, status

from app.core.container import Container
from app.services.oauth import OAuthService
from app.utils.service_utils import is_service_enabled


def get_oauth_service() -> OAuthService:
    """Dependency that ensures OAuth service is enabled.

    Returns:
    -------
        OAuthService instance if enabled

    Raises:
    ------
        HTTPException: If OAuth service is disabled (503 Service Unavailable)

    Examples:
    --------
        >>> @router.get("/oauth/authorize")
        ... async def authorize(
        ...     oauth_service: OAuthService = Depends(get_oauth_service)
        ... ):
        ...     # OAuth service is guaranteed to be enabled here
        ...     pass

    """
    config = Container.config()
    service = Container.oauth_service()

    if not is_service_enabled(service, "oauth_service", config):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OAuth service is not available",
        )

    return service


__all__ = ["get_oauth_service"]
