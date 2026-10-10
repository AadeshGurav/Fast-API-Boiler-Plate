"""Personal access tokens: long-lived, revocable credentials for scripts and integrations.

A token is ``fabp_pat_`` plus 43 random characters. It is shown once and stored only as its
SHA-256 hash. It carries ``scopes``, and a request made with it may use a permission only if
both its owner holds it and its scopes cover it (``RBACService.allows``), so a token can never
do more than its owner, and narrowing a user's roles narrows their tokens immediately.
"""

from __future__ import annotations

import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from app.models.auth import TokenPayload
from app.services.data.policies import CachePolicy
from app.services.data.sessions_ops import hash_token

if TYPE_CHECKING:
    from app.services.audit import AuditService
    from app.services.data import DataService
    from config import Config

COLLECTION = "api_tokens"
PREFIX = "fabp_pat_"
DB = CachePolicy.DB_ONLY
SCOPE_PATTERN = re.compile(r"^(\*|[a-z][a-z0-9_-]*:(\*|[a-z][a-z0-9_-]*))$")
LAST_USED_RESOLUTION = timedelta(minutes=1)  # bounds writes to one per token per minute


class ApiTokenError(ValueError):
    """The token request was refused; the message is safe to show."""


def is_api_token(value: str | None) -> bool:
    return bool(value) and value.startswith(PREFIX)


def public_view(record: dict[str, Any]) -> dict[str, Any]:
    """Token metadata that is safe to show (never the hash)."""
    return {
        key: record.get(key)
        for key in ("id", "name", "prefix", "scopes", "created_at", "expires_at", "last_used_at")
    }


class ApiTokenManager:
    """Create, list, revoke and authenticate personal access tokens."""

    def __init__(self, config: Config, data_service: DataService, audit: AuditService) -> None:
        self.data_service = data_service
        self.audit = audit
        self.max_days: int = config["api_token_max_days"]
        self.per_user: int = config["api_tokens_per_user"]

    async def create(
        self, user_id: str, name: str, scopes: list[str], expires_in_days: int
    ) -> tuple[str, dict[str, Any]]:
        """Issue a token; returns (the token, shown once; its public metadata)."""
        invalid = [scope for scope in scopes if not SCOPE_PATTERN.match(scope)]
        if invalid:
            raise ApiTokenError(
                f"Invalid scopes: {invalid}. Use 'resource:action', 'resource:*' or '*'"
            )
        if not 1 <= expires_in_days <= self.max_days:
            raise ApiTokenError(f"expires_in_days must be between 1 and {self.max_days}")
        if await self.data_service.count(COLLECTION, {"user_id": user_id}) >= self.per_user:
            raise ApiTokenError(f"You already have {self.per_user} tokens; revoke one first")

        token = PREFIX + secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        record = {
            "id": uuid.uuid4().hex,
            "user_id": user_id,
            "name": name,
            "prefix": token[: len(PREFIX) + 6],
            "token_hash": hash_token(token),
            "scopes": sorted(set(scopes)),
            "created_at": now,
            "expires_at": now + timedelta(days=expires_in_days),
            "last_used_at": None,
        }
        await self.data_service.insert(COLLECTION, record)
        await self.audit.record(
            "token.created",
            target_type="api_token",
            target_id=record["id"],
            details={"name": name, "scopes": ",".join(record["scopes"])},
        )
        return token, public_view(record)

    async def list_for(self, user_id: str, page: int, page_size: int) -> tuple[list[dict], int]:
        records = await self.data_service.find_many(
            COLLECTION,
            {"user_id": user_id},
            policy=DB,
            sort=[("created_at", -1), ("id", -1)],
            skip=(page - 1) * page_size,
            limit=page_size,
        )
        total = await self.data_service.count(COLLECTION, {"user_id": user_id})
        return [public_view(r) for r in records], total

    async def revoke(self, user_id: str, token_id: str) -> bool:
        """Delete one of the user's tokens; it stops working on the next request."""
        deleted = await self.data_service.delete(
            COLLECTION, {"id": token_id, "user_id": user_id}, policy=DB
        )
        if deleted:
            await self.audit.record("token.revoked", target_type="api_token", target_id=token_id)
        return deleted

    async def authenticate(self, token: str) -> TokenPayload | None:
        """The caller a valid, unexpired token belongs to, if the owner is still active."""
        record = await self.data_service.get(
            COLLECTION, {"token_hash": hash_token(token)}, policy=DB
        )
        now = datetime.now(UTC)
        if not record or record["expires_at"] <= now:
            return None
        user = await self.data_service.users.get_user_by_id(record["user_id"], fresh=True)
        if not user or user.get("status", "active") != "active":
            return None
        last_used = record.get("last_used_at")
        if last_used is None or now - last_used > LAST_USED_RESOLUTION:
            await self.data_service.update(
                COLLECTION, {"id": record["id"]}, {"last_used_at": now}, policy=DB
            )
        return TokenPayload(
            user_id=user["id"],
            username=user["username"],
            roles=user.get("roles", []),
            exp=record["expires_at"],
            type="api_token",
            scopes=record["scopes"],
        )
