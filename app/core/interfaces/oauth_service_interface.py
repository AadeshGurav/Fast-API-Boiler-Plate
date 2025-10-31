"""OAuth service interface for platform-agnostic OAuth operations."""
from __future__ import annotations

from abc import abstractmethod

from app.core.interfaces.base_interface import BaseInterface
from app.models.oauth import OAuthProvider, OAuthToken, OAuthUserInfo
from app.models.user import User


class OAuthServiceInterface(BaseInterface):
    """Interface for OAuth service operations."""

    @abstractmethod
    def get_authorization_url(self, provider: OAuthProvider, state: str) -> str:
        """Get OAuth authorization URL.

        Args:
            provider: OAuth provider
            state: State parameter for security

        Returns:
            Authorization URL

        """
        pass

    @abstractmethod
    async def exchange_code_for_token(
        self, provider: OAuthProvider, code: str
    ) -> OAuthToken:
        """Exchange authorization code for tokens.

        Args:
            provider: OAuth provider
            code: Authorization code

        Returns:
            OAuth tokens

        """
        pass

    @abstractmethod
    async def get_user_info(
        self, provider: OAuthProvider, access_token: str
    ) -> OAuthUserInfo:
        """Get user information from OAuth provider.

        Args:
            provider: OAuth provider
            access_token: OAuth access token

        Returns:
            User information

        """
        pass

    @abstractmethod
    async def create_or_link_user(
        self, oauth_user_info: OAuthUserInfo, provider: OAuthProvider
    ) -> User:
        """Create or link user from OAuth information.

        Args:
            oauth_user_info: OAuth user information
            provider: OAuth provider

        Returns:
            User object

        """
        pass

    @abstractmethod
    async def unlink_oauth_account(self, user_id: str, provider: OAuthProvider) -> bool:
        """Unlink OAuth account from user.

        Args:
            user_id: User identifier
            provider: OAuth provider

        Returns:
            True if unlinked successfully

        """
        pass


__all__ = ["OAuthServiceInterface"]
