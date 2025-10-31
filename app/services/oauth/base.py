"""Base OAuth functionality."""

from __future__ import annotations

import secrets
import urllib.parse

import httpx

from app.core.interfaces.oauth_repository_interface import OAuthRepositoryInterface
from app.core.interfaces.user_repository_interface import UserRepositoryInterface
from app.models.oauth import OAuthAccount, OAuthProvider, OAuthToken, OAuthUserInfo
from app.models.user import User, UserCreate, UserRole
from app.services.logger import Logger
from config import Config


class OAuthBase:
    """Base OAuth functionality."""

    def __init__(
        self: OAuthBase,
        config: Config,
        logger: Logger,
        oauth_repository: OAuthRepositoryInterface,
        user_repository: UserRepositoryInterface,
    ):
        """Initialize OAuth base.

        Args:
        ----
            config: Configuration instance
            logger: Logger instance
            oauth_repository: OAuth repository interface
            user_repository: User repository interface

        """
        self.config = config
        self.logger = logger
        self.oauth_repository = oauth_repository
        self.user_repository = user_repository

        # Load OAuth provider configurations
        self.providers = self.config.get("oauth_providers", {})
        self.oauth_enabled = self.config.get("oauth_enabled", False)

        self.logger.info(
            f"OAuth service initialized: enabled={self.oauth_enabled}, providers={list(self.providers.keys())}",
            extra={
                "service": "oauth",
                "action": "initialize",
                "providers": list(self.providers.keys()),
                "enabled": self.oauth_enabled,
            },
        )

    def get_authorization_url(self, provider: OAuthProvider, state: str) -> str:
        """Get OAuth authorization URL for the provider.

        Args:
        ----
            provider: OAuth provider
            state: State parameter for CSRF protection

        Returns:
        -------
            Authorization URL

        Raises:
        ------
            ValueError: If provider is not configured

        """
        provider_config = self.providers.get(provider.value)
        if not provider_config:
            self.logger.error(
                f"OAuth provider not configured: {provider.value}",
                extra={
                    "service": "oauth",
                    "action": "get_authorization_url",
                    "provider": provider.value,
                    "error": "provider_not_configured",
                },
            )
            raise ValueError(f"OAuth provider {provider.value} is not configured")

        params = {
            "client_id": provider_config["client_id"],
            "redirect_uri": provider_config["redirect_uri"],
            "scope": " ".join(provider_config["scopes"]),
            "response_type": "code",
            "state": state,
        }

        if provider == OAuthProvider.GOOGLE:
            params["access_type"] = "offline"
            params["prompt"] = "consent"

        auth_url = provider_config["authorization_url"]
        query_string = urllib.parse.urlencode(params)
        full_url = f"{auth_url}?{query_string}"

        self.logger.info(
            f"OAuth authorization URL generated: {provider.value}",
            extra={
                "service": "oauth",
                "action": "get_authorization_url",
                "provider": provider.value,
                "state": state,
            },
        )

        return full_url

    async def exchange_code_for_token(
        self, provider: OAuthProvider, code: str
    ) -> OAuthToken:
        """Exchange authorization code for access token.

        Args:
        ----
            provider: OAuth provider
            code: Authorization code from callback

        Returns:
        -------
            OAuth token information

        Raises:
        ------
            ValueError: If provider is not configured
            httpx.HTTPError: If token exchange fails

        """
        provider_config = self.providers.get(provider.value)
        if not provider_config:
            self.logger.error(
                f"OAuth provider not configured: {provider.value}",
                extra={
                    "service": "oauth",
                    "action": "exchange_code_for_token",
                    "provider": provider.value,
                    "error": "provider_not_configured",
                },
            )
            raise ValueError(f"OAuth provider {provider.value} is not configured")

        token_data = {
            "client_id": provider_config["client_id"],
            "client_secret": provider_config["client_secret"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": provider_config["redirect_uri"],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                provider_config["token_url"],
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()

            token_response = response.json()

            oauth_token = OAuthToken(
                access_token=token_response["access_token"],
                refresh_token=token_response.get("refresh_token"),
                expires_in=token_response.get("expires_in", 3600),
                token_type=token_response.get("token_type", "Bearer"),
                scope=token_response.get("scope"),
            )

            self.logger.info(
                f"OAuth token exchanged successfully: {provider.value}",
                extra={
                    "service": "oauth",
                    "action": "exchange_code_for_token",
                    "provider": provider.value,
                    "expires_in": oauth_token.expires_in,
                },
            )

            return oauth_token

    async def create_or_link_user(
        self, oauth_user_info: OAuthUserInfo, provider: OAuthProvider
    ) -> User:
        """Create new user or link existing user with OAuth account.

        Args:
        ----
            oauth_user_info: User information from OAuth provider
            provider: OAuth provider

        Returns:
        -------
            User instance

        """
        # Check if OAuth account already exists
        existing_oauth = await self.oauth_repository.get_oauth_account(
            provider.value, oauth_user_info.provider_user_id
        )

        if existing_oauth:
            # Link exists, get the user
            user = await self.user_repository.get_user_by_id(existing_oauth["user_id"])
            if user:
                self.logger.info(
                    f"Existing OAuth account linked: {provider.value}",
                    extra={
                        "service": "oauth",
                        "action": "create_or_link_user",
                        "provider": provider.value,
                        "user_id": user["id"],
                        "provider_user_id": oauth_user_info.provider_user_id,
                    },
                )
                return User(**user)

        # Check if user exists by email
        existing_user = None
        if oauth_user_info.email:
            existing_user = await self.user_repository.get_user_by_email(
                oauth_user_info.email
            )

        if existing_user:
            # Link OAuth account to existing user
            oauth_account = OAuthAccount(
                user_id=existing_user["id"],
                provider=provider,
                provider_user_id=oauth_user_info.provider_user_id,
                access_token="",  # Will be updated separately
                refresh_token=None,
            )

            await self.oauth_repository.link_oauth_account(oauth_account.dict())

            self.logger.info(
                f"OAuth account linked to existing user: {provider.value}",
                extra={
                    "service": "oauth",
                    "action": "create_or_link_user",
                    "provider": provider.value,
                    "user_id": existing_user["id"],
                    "provider_user_id": oauth_user_info.provider_user_id,
                },
            )

            return User(**existing_user)

        # Create new user
        username = (
            oauth_user_info.email.split("@")[0]
            if oauth_user_info.email
            else f"user_{secrets.token_hex(4)}"
        )

        # Ensure username is unique
        counter = 1
        original_username = username
        while await self.user_repository.get_user_by_username(username):
            username = f"{original_username}_{counter}"
            counter += 1

        user_create = UserCreate(
            username=username,
            email=oauth_user_info.email or f"{username}@oauth.local",
            password="",  # OAuth users don't have passwords
            roles=[UserRole.USER.value],
            groups=[],
        )

        user_data = await self.user_repository.create_user(user_create.dict())
        user = User(**user_data)

        # Link OAuth account
        oauth_account = OAuthAccount(
            user_id=user.id,
            provider=provider,
            provider_user_id=oauth_user_info.provider_user_id,
            access_token="",  # Will be updated separately
            refresh_token=None,
        )

        await self.oauth_repository.link_oauth_account(oauth_account.dict())

        self.logger.info(
            f"New user created and OAuth account linked: {provider.value}",
            extra={
                "service": "oauth",
                "action": "create_or_link_user",
                "provider": provider.value,
                "user_id": user.id,
                "username": user.username,
                "provider_user_id": oauth_user_info.provider_user_id,
            },
        )

        return user

    async def unlink_oauth_account(self, user_id: str, provider: OAuthProvider) -> bool:
        """Unlink OAuth account from user.

        Args:
        ----
            user_id: User ID
            provider: OAuth provider

        Returns:
        -------
            True if successfully unlinked

        """
        result = await self.oauth_repository.unlink_oauth_account(
            user_id, provider.value
        )

        if result:
            self.logger.info(
                f"OAuth account unlinked: {provider.value}",
                extra={
                    "service": "oauth",
                    "action": "unlink_oauth_account",
                    "provider": provider.value,
                    "user_id": user_id,
                },
            )

        return result

    async def update_oauth_tokens(
        self, user_id: str, provider: OAuthProvider, tokens: OAuthToken
    ) -> bool:
        """Update OAuth tokens for user.

        Args:
        ----
            user_id: User ID
            provider: OAuth provider
            tokens: Updated OAuth tokens

        Returns:
        -------
            True if successfully updated

        """
        result = await self.oauth_repository.update_oauth_tokens(
            user_id, provider.value, tokens.dict()
        )

        if result:
            self.logger.info(
                f"OAuth tokens updated: {provider.value}",
                extra={
                    "service": "oauth",
                    "action": "update_oauth_tokens",
                    "provider": provider.value,
                    "user_id": user_id,
                },
            )

        return result


__all__ = ["OAuthBase"]
