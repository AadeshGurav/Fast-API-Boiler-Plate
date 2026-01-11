"""Google OAuth provider implementation."""

from __future__ import annotations

import httpx

from app.models.oauth import OAuthProvider, OAuthUserInfo
from app.services.logger import Logger


class GoogleOAuthProvider:
    """Google OAuth provider implementation."""

    def __init__(self, logger: Logger):
        """Initialize Google OAuth provider.

        Args:
            logger: Logger instance

        """
        self.logger = logger

    async def get_user_info(
        self, provider_config: dict, access_token: str
    ) -> OAuthUserInfo:
        """Get user information from Google OAuth provider.

        Args:
            provider_config: Provider configuration
            access_token: OAuth access token

        Returns:
            User information from Google

        Raises:
            httpx.HTTPError: If user info request fails

        """
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                provider_config["userinfo_url"],
                headers=headers,
            )
            response.raise_for_status()

            user_data = response.json()

            oauth_user_info = OAuthUserInfo(
                provider_user_id=user_data["id"],
                email=user_data["email"],
                name=user_data.get("name", ""),
                picture=user_data.get("picture"),
            )

            self.logger.info(
                "Google OAuth user info retrieved",
                extra={
                    "service": "oauth",
                    "action": "get_user_info",
                    "provider": OAuthProvider.GOOGLE.value,
                    "provider_user_id": oauth_user_info.provider_user_id,
                    "email": oauth_user_info.email,
                },
            )

            return oauth_user_info


__all__ = ["GoogleOAuthProvider"]
