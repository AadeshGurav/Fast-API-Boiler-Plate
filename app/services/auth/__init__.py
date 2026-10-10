"""Authentication service package."""

from __future__ import annotations

from app.services.auth.service import AuthenticationError, AuthService

__all__ = ["AuthService", "AuthenticationError"]
