"""OAuth providers package initialization."""
from __future__ import annotations

from app.services.oauth.providers.apple import AppleOAuthProvider
from app.services.oauth.providers.google import GoogleOAuthProvider

__all__ = ["GoogleOAuthProvider", "AppleOAuthProvider"]
