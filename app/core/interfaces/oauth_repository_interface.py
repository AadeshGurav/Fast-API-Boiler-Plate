"""OAuth repository interface for platform-agnostic OAuth operations."""
from __future__ import annotations

from abc import abstractmethod

from app.core.interfaces.base_interface import BaseInterface


class OAuthRepositoryInterface(BaseInterface):
    """Interface for OAuth repository operations."""

    @abstractmethod
    async def link_oauth_account(self, oauth_account: dict) -> bool:
        """Link OAuth account to user.

        Args:
            oauth_account: OAuth account data

        Returns:
            True if linked successfully

        """
        pass

    @abstractmethod
    async def get_oauth_account(
        self, provider: str, provider_user_id: str
    ) -> dict | None:
        """Get OAuth account by provider and provider user ID.

        Args:
            provider: OAuth provider
            provider_user_id: Provider user ID

        Returns:
            OAuth account data or None if not found

        """
        pass

    @abstractmethod
    async def get_user_oauth_accounts(self, user_id: str) -> list[dict]:
        """Get all OAuth accounts for a user.

        Args:
            user_id: User identifier

        Returns:
            List of OAuth account data

        """
        pass

    @abstractmethod
    async def unlink_oauth_account(self, user_id: str, provider: str) -> bool:
        """Unlink OAuth account from user.

        Args:
            user_id: User identifier
            provider: OAuth provider

        Returns:
            True if unlinked successfully

        """
        pass

    @abstractmethod
    async def update_oauth_tokens(
        self, user_id: str, provider: str, tokens: dict
    ) -> bool:
        """Update OAuth tokens for user.

        Args:
            user_id: User identifier
            provider: OAuth provider
            tokens: Token data

        Returns:
            True if updated successfully

        """
        pass


__all__ = ["OAuthRepositoryInterface"]
