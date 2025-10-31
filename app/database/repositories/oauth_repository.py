"""MongoDB OAuth repository implementation."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.interfaces.oauth_repository_interface import OAuthRepositoryInterface
from app.services.database_service import DatabaseService
from app.services.logger import Logger


class OAuthRepository(OAuthRepositoryInterface):
    """MongoDB implementation of OAuth repository."""

    def __init__(self, database_service: DatabaseService, logger: Logger):
        """Initialize OAuth repository.

        Args:
            database_service: Database service instance
            logger: Logger instance

        """
        self.database_service = database_service
        self.logger = logger
        self.collection = "oauth_accounts"

    async def link_oauth_account(self, oauth_account: dict) -> bool:
        """Link OAuth account to user.

        Args:
            oauth_account: OAuth account data

        Returns:
            True if linked successfully

        """
        oauth_account["id"] = str(uuid.uuid4())
        oauth_account["created_at"] = datetime.now(timezone.utc)
        oauth_account["updated_at"] = datetime.now(timezone.utc)

        await self.database_service.insert_record(self.collection, oauth_account)

        self.logger.info(
            f"OAuth account linked: {oauth_account['user_id']}",
            extra={
                "action": "link_oauth_account",
                "user_id": oauth_account["user_id"],
                "provider": oauth_account["provider"],
                "provider_user_id": oauth_account["provider_user_id"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return True

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
        account = await self.database_service.get_record(
            self.collection,
            {"provider": provider, "provider_user_id": provider_user_id},
        )

        if account:
            self.logger.debug(
                f"OAuth account retrieved: {provider}:{provider_user_id}",
                extra={
                    "action": "get_oauth_account",
                    "provider": provider,
                    "provider_user_id": provider_user_id,
                    "user_id": account.get("user_id"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        else:
            self.logger.debug(
                f"OAuth account not found: {provider}:{provider_user_id}",
                extra={
                    "action": "get_oauth_account",
                    "provider": provider,
                    "provider_user_id": provider_user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        return account

    async def get_user_oauth_accounts(self, user_id: str) -> list[dict]:
        """Get all OAuth accounts for a user.

        Args:
            user_id: User identifier

        Returns:
            List of OAuth account data

        """
        # This would need a custom query method
        # For now, we'll use a simple approach
        accounts = await self.database_service.execute_query(
            f"SELECT * FROM {self.collection} WHERE user_id = :user_id",
            {"user_id": user_id},
        )

        self.logger.debug(
            f"User OAuth accounts retrieved: {user_id}",
            extra={
                "action": "get_user_oauth_accounts",
                "user_id": user_id,
                "account_count": len(accounts) if accounts else 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return accounts or []

    async def unlink_oauth_account(self, user_id: str, provider: str) -> bool:
        """Unlink OAuth account from user.

        Args:
            user_id: User identifier
            provider: OAuth provider

        Returns:
            True if unlinked successfully

        """
        result = await self.database_service.delete_record(
            self.collection, {"user_id": user_id, "provider": provider}
        )

        if result:
            self.logger.info(
                f"OAuth account unlinked: {user_id}:{provider}",
                extra={
                    "action": "unlink_oauth_account",
                    "user_id": user_id,
                    "provider": provider,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        else:
            self.logger.warning(
                f"OAuth account unlink failed: {user_id}:{provider}",
                extra={
                    "action": "unlink_oauth_account",
                    "user_id": user_id,
                    "provider": provider,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        return result

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
        updates = {
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "updated_at": datetime.now(timezone.utc),
        }

        result = await self.database_service.update_record(
            self.collection, {"user_id": user_id, "provider": provider}, updates
        )

        if result:
            self.logger.info(
                f"OAuth tokens updated: {user_id}:{provider}",
                extra={
                    "action": "update_oauth_tokens",
                    "user_id": user_id,
                    "provider": provider,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        else:
            self.logger.warning(
                f"OAuth tokens update failed: {user_id}:{provider}",
                extra={
                    "action": "update_oauth_tokens",
                    "user_id": user_id,
                    "provider": provider,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        return result


__all__ = ["OAuthRepository"]
