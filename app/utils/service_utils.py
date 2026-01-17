"""Utility functions for checking service availability and enabled status."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from config import Config


def is_service_enabled(
    service: Any, feature_flag: str | None = None, config: Config | None = None
) -> bool:
    """Check if a service is enabled and available.

    This function checks multiple conditions to determine if a service is enabled:
    1. Service is not None
    2. Service has is_enabled() method that returns True
    3. Service has enabled attribute that is True
    4. Feature flag in config is enabled (if provided)

    Args:
    ----
        service: Service instance (may be None)
        feature_flag: Optional feature flag name for config check (e.g., "oauth_service")
        config: Optional config instance for feature flag check

    Returns:
    -------
        True if service is available and enabled, False otherwise

    Examples:
    --------
        >>> is_service_enabled(metrics_service)
        True

        >>> is_service_enabled(oauth_service, "oauth_service", config)
        False

    """
    # Service must exist
    if service is None:
        return False

    # Check feature flag in config if provided
    if feature_flag and config:
        flag_value = config.get(feature_flag)
        if flag_value is False:
            return False

    # Check if service has is_enabled() method (like SentryService)
    if hasattr(service, "is_enabled"):
        try:
            if callable(service.is_enabled):
                return bool(service.is_enabled())
            return bool(service.is_enabled)
        except Exception:  # noqa: BLE001
            return False

    # Check if service has enabled attribute (like MetricsService, TracingService)
    if hasattr(service, "enabled"):
        try:
            return bool(service.enabled)
        except Exception:  # noqa: BLE001
            return False

    # If service exists but has no enabled/is_enabled indicator,
    # assume it's enabled (backward compatibility)
    return True


__all__ = ["is_service_enabled"]
