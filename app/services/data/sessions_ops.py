from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from .policies import CachePolicy

if TYPE_CHECKING:
    from .data_service import DataService


def hash_token(token: str) -> str:
    """SHA-256 hex digest used to store and compare refresh tokens."""
    return hashlib.sha256(token.encode()).hexdigest()


def is_session_active(session: dict[str, Any] | None) -> bool:
    """A session is usable if it exists, is not revoked and has not expired."""
    if not session or session.get("revoked_at"):
        return False
    expires_at = session.get("expires_at")
    return isinstance(expires_at, datetime) and expires_at > datetime.now(UTC)


class SessionsOps:
    """Session-related data operations using core CRUD with cache policy."""

    def __init__(self: SessionsOps, data_service: DataService) -> None:
        """Initialize SessionsOps.

        Args:
        ----
            data_service: DataService instance.

        """
        self.ds = data_service
        self.collection = "sessions"

    @staticmethod
    def _cache_key(session_id: str) -> str:
        return f"session:{session_id}"

    async def create_session(self: SessionsOps, session_data: dict[str, Any]) -> str:
        """Create a new session.

        Args:
        ----
            session_data: Session data dictionary.

        Returns:
        -------
            Session ID.

        """
        session_id = session_data.get("id") or uuid.uuid4().hex
        session_data = {**session_data, "id": session_id}
        session_data.setdefault("created_at", datetime.now(UTC))
        session_data.setdefault("revoked_at", None)
        # Never store the refresh token itself, only its hash.
        if "refresh_token" in session_data:
            session_data["refresh_token_hash"] = hash_token(session_data.pop("refresh_token"))

        await self.ds.set(
            self.collection,
            {"id": session_id},
            session_data,
            policy=CachePolicy.AUTO,
            key=self._cache_key(session_id),
        )
        return session_id

    async def get_session(self: SessionsOps, session_id: str) -> dict[str, Any] | None:
        """Get session by ID.

        Args:
        ----
            session_id: Session ID.

        Returns:
        -------
            Session dictionary or None if not found.

        """
        return await self.ds.get(
            self.collection,
            {"id": session_id},
            policy=CachePolicy.AUTO,
            key=self._cache_key(session_id),
        )

    async def get_user_sessions(self: SessionsOps, user_id: str) -> list[dict[str, Any]]:
        """Get all sessions for a user.

        Args:
        ----
            user_id: User ID.

        Returns:
        -------
            List of session dictionaries.

        """
        # list queries default to DB_ONLY unless explicitly cached
        return await self.ds.find_many(self.collection, {"user_id": user_id})

    async def update_session(self: SessionsOps, session_id: str, updates: dict[str, Any]) -> bool:
        """Update session data.

        Args:
        ----
            session_id: Session ID.
            updates: Update dictionary.

        Returns:
        -------
            True if successful, False otherwise.

        """
        updates = {"updated_at": datetime.now(UTC), **updates}
        # AUTO: the update invalidates the cached copy, so the next read is fresh.
        return await self.ds.update(
            self.collection,
            {"id": session_id},
            updates,
            key=self._cache_key(session_id),
            policy=CachePolicy.AUTO,
        )

    async def revoke_session(self: SessionsOps, session_id: str) -> bool:
        """Revoke a session.

        Args:
        ----
            session_id: Session ID.

        Returns:
        -------
            True if successful, False otherwise.

        """
        return await self.update_session(session_id, {"revoked_at": datetime.now(UTC)})

    async def revoke_user_sessions(
        self: SessionsOps, user_id: str, except_session_id: str | None = None
    ) -> int:
        """Revoke all sessions for a user except specified one.

        Args:
        ----
            user_id: User ID.
            except_session_id: Session ID to exclude from revocation.

        Returns:
        -------
            Number of sessions revoked.

        """
        now = datetime.now(UTC)
        live = [
            s["id"]
            for s in await self.get_user_sessions(user_id)
            if is_session_active(s) and s["id"] != except_session_id
        ]
        if not live:
            return 0
        # One write for the database, then drop each cached copy so no stale "active"
        # session is served.
        await self.ds.update_many(
            self.collection,
            {"user_id": user_id, "id": {"$in": live}},
            {"revoked_at": now, "updated_at": now},
        )
        for session_id in live:
            await self.ds.cache_service.delete(self._cache_key(session_id))
        return len(live)
