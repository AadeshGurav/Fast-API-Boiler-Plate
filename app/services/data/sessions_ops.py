from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from .policies import CachePolicy

if TYPE_CHECKING:
    from .data_service import DataService


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

    async def create_session(self: SessionsOps, session_data: dict[str, Any]) -> str:
        """Create a new session.

        Args:
        ----
            session_data: Session data dictionary.

        Returns:
        -------
            Session ID.

        """
        session_id = session_data.get("id") or str(uuid.uuid4())
        session_data["id"] = session_id
        session_data.setdefault("created_at", datetime.now(timezone.utc))
        # Hash refresh token if present
        if "refresh_token" in session_data:
            session_data["refresh_token"] = hashlib.sha256(
                session_data["refresh_token"].encode()
            ).hexdigest()

        await self.ds.set(
            self.collection,
            {"id": session_id},
            session_data,
            policy=CachePolicy.AUTO,
            key=f"session:{session_id}",
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
            key=f"session:{session_id}",
        )

    async def get_user_sessions(
        self: SessionsOps, user_id: str
    ) -> list[dict[str, Any]]:
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

    async def update_session(
        self: SessionsOps, session_id: str, updates: dict[str, Any]
    ) -> bool:
        """Update session data.

        Args:
        ----
            session_id: Session ID.
            updates: Update dictionary.

        Returns:
        -------
            True if successful, False otherwise.

        """
        updates.setdefault("updated_at", datetime.now(timezone.utc))
        ok = await self.ds.set(
            self.collection,
            {"id": session_id},
            updates,
            policy=CachePolicy.DB_ONLY,
        )
        # Purge and refresh cache
        await self.ds.delete(
            self.collection,
            {"id": session_id},
            policy=CachePolicy.CACHE_ONLY,
            key=f"session:{session_id}",
        )
        refreshed = await self.get_session(session_id)
        if refreshed:
            await self.ds.set(
                self.collection,
                {"id": session_id},
                refreshed,
                policy=CachePolicy.CACHE_ONLY,
                key=f"session:{session_id}",
            )
        return ok

    async def revoke_session(self: SessionsOps, session_id: str) -> bool:
        """Revoke a session.

        Args:
        ----
            session_id: Session ID.

        Returns:
        -------
            True if successful, False otherwise.

        """
        return await self.update_session(
            session_id, {"revoked_at": datetime.now(timezone.utc)}
        )

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
        sessions = await self.get_user_sessions(user_id)
        count = 0
        for s in sessions:
            if except_session_id and s.get("id") == except_session_id:
                continue
            if await self.revoke_session(s["id"]):
                count += 1
        return count
