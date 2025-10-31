"""Main OAuth service combining all OAuth functionality."""
from __future__ import annotations

from app.core.interfaces.oauth_repository_interface import OAuthRepositoryInterface
from app.core.interfaces.oauth_service_interface import OAuthServiceInterface
from app.core.interfaces.user_repository_interface import UserRepositoryInterface
from app.models.oauth import OAuthProvider, OAuthToken, OAuthUserInfo
from app.models.user import User
from app.services.logger import Logger
from app.services.oauth.base import OAuthBase
from app.services.oauth.providers import AppleOAuthProvider, GoogleOAuthProvider
from config import Config


class OAuthService(OAuthServiceInterface, OAuthBase):
    """OAuth service implementation for Google and Apple providers."""

    def __init__(
        self,
        config: Config,
        logger: Logger,
        oauth_repository: OAuthRepositoryInterface,
        user_repository: UserRepositoryInterface,
    ):
        """Initialize OAuth service.

        Args:
            config: Configuration instance
            logger: Logger instance
            oauth_repository: OAuth repository interface
            user_repository: User repository interface

        """
        OAuthBase.__init__(self, config, logger, oauth_repository, user_repository)

        # Initialize provider-specific implementations
        self.google_provider = GoogleOAuthProvider(logger)
        self.apple_provider = AppleOAuthProvider(logger)

    # Interface implementation methods
    def get_authorization_url(self, provider: OAuthProvider, state: str) -> str:
        """Get OAuth authorization URL."""
        return super().get_authorization_url(provider, state)

    async def exchange_code_for_token(
        self, provider: OAuthProvider, code: str
    ) -> OAuthToken:
        """Exchange authorization code for tokens."""
        return await super().exchange_code_for_token(provider, code)

    async def get_user_info(
        self, provider: OAuthProvider, access_token: str
    ) -> OAuthUserInfo:
        """Get user information from OAuth provider.

        Args:
            provider: OAuth provider
            access_token: OAuth access token

        Returns:
            User information from provider

        Raises:
            ValueError: If provider is not configured
            httpx.HTTPError: If user info request fails

        """
        provider_config = self.providers.get(provider.value)
        if not provider_config:
            self.logger.error(
                f"OAuth provider not configured: {provider.value}",
                extra={
                    "service": "oauth",
                    "action": "get_user_info",
                    "provider": provider.value,
                    "error": "provider_not_configured",
                },
            )
            raise ValueError(f"OAuth provider {provider.value} is not configured")

        # Use provider-specific implementation
        if provider == OAuthProvider.GOOGLE:
            return await self.google_provider.get_user_info(
                provider_config, access_token
            )
        elif provider == OAuthProvider.APPLE:
            return await self.apple_provider.get_user_info(
                provider_config, access_token
            )
        else:
            raise ValueError(f"Unsupported OAuth provider: {provider.value}")

    async def create_or_link_user(
        self, oauth_user_info: OAuthUserInfo, provider: OAuthProvider
    ) -> User:
        """Create or link user from OAuth information."""
        return await super().create_or_link_user(oauth_user_info, provider)

    async def unlink_oauth_account(self, user_id: str, provider: OAuthProvider) -> bool:
        """Unlink OAuth account from user."""
        return await super().unlink_oauth_account(user_id, provider)


__all__ = ["OAuthService"]
