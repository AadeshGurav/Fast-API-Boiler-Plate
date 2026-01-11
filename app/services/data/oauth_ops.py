from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from .policies import CachePolicy

if TYPE_CHECKING:
    from .data_service import DataService


class OAuthOps:
    """OAuth-related data operations using core CRUD with cache policy."""

    def __init__(self: OAuthOps, data_service: DataService) -> None:
        """Initialize OAuthOps.

        Args:
        ----
            data_service: DataService instance.

        """
        self.ds = data_service
        self.collection = "oauth_accounts"

    async def link_oauth_account(self: OAuthOps, oauth_account: dict[str, Any]) -> bool:
        """Link OAuth account to user.

        Args:
        ----
            oauth_account: OAuth account data dictionary.

        Returns:
        -------
            True if successful, False otherwise.

        """
        oauth_account["id"] = str(uuid.uuid4())
        oauth_account["created_at"] = datetime.now(timezone.utc)
        oauth_account["updated_at"] = datetime.now(timezone.utc)

        await self.ds.set(
            self.collection,
            {"id": oauth_account["id"]},
            oauth_account,
            policy=CachePolicy.DB_ONLY,
        )

        return True

    async def get_oauth_account(
        self: OAuthOps, provider: str, provider_user_id: str
    ) -> dict[str, Any] | None:
        """Get OAuth account by provider and provider user ID.

        Args:
        ----
            provider: OAuth provider name.
            provider_user_id: Provider user ID.

        Returns:
        -------
            OAuth account dictionary or None if not found.

        """
        account = await self.ds.get(
            self.collection,
            {"provider": provider, "provider_user_id": provider_user_id},
            policy=CachePolicy.AUTO,
        )
        return account

    async def get_user_oauth_accounts(
        self: OAuthOps, user_id: str
    ) -> list[dict[str, Any]]:
        """Get all OAuth accounts for a user.

        Args:
        ----
            user_id: User ID.

        Returns:
        -------
            List of OAuth account dictionaries.

        """
        accounts = await self.ds.find_many(
            self.collection, {"user_id": user_id}, policy=CachePolicy.DB_ONLY
        )
        return accounts or []

    async def unlink_oauth_account(self: OAuthOps, user_id: str, provider: str) -> bool:
        """Unlink OAuth account from user.

        Args:
        ----
            user_id: User ID.
            provider: OAuth provider name.

        Returns:
        -------
            True if successful, False otherwise.

        """
        return await self.ds.delete(
            self.collection,
            {"user_id": user_id, "provider": provider},
            policy=CachePolicy.DB_ONLY,
        )

    async def update_oauth_tokens(
        self: OAuthOps, user_id: str, provider: str, tokens: dict[str, Any]
    ) -> bool:
        """Update OAuth tokens for user.

        Args:
        ----
            user_id: User ID.
            provider: OAuth provider name.
            tokens: Token data dictionary.

        Returns:
        -------
            True if successful, False otherwise.

        """
        updates = {
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "updated_at": datetime.now(timezone.utc),
        }

        return await self.ds.set(
            self.collection,
            {"user_id": user_id, "provider": provider},
            updates,
            policy=CachePolicy.DB_ONLY,
        )
