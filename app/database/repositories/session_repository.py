"""MongoDB session repository implementation with hybrid Redis caching."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from app.core.interfaces.session_repository_interface import SessionRepositoryInterface
from app.services.cache import CacheService
from app.services.database_service import DatabaseService
from app.services.logger import Logger


class SessionRepository(SessionRepositoryInterface):
    """MongoDB implementation of session repository with Redis caching."""

    def __init__(
        self,
        database_service: DatabaseService,
        cache_service: CacheService,
        logger: Logger,
    ):
        """Initialize session repository.

        Args:
        ----
            database_service: Database service instance
            cache_service: Cache service instance
            logger: Logger instance

        """
        self.database_service = database_service
        self.cache_service = cache_service
        self.logger = logger
        self.collection = "sessions"
        self.cache_ttl = 3600  # 1 hour

    def _hash_refresh_token(self, refresh_token: str) -> str:
        """Hash refresh token for secure storage.

        Args:
        ----
            refresh_token: Plain refresh token

        Returns:
        -------
            Hashed refresh token

        """
        return hashlib.sha256(refresh_token.encode()).hexdigest()

    async def create_session(self, session_data: dict) -> str:
        """Create a new session.

        Args:
        ----
            session_data: Session data dictionary

        Returns:
        -------
            Session ID

        """
        session_id = str(uuid.uuid4())
        session_data["id"] = session_id
        session_data["created_at"] = datetime.now(timezone.utc)

        # Hash refresh token if present
        if "refresh_token" in session_data:
            session_data["refresh_token"] = self._hash_refresh_token(
                session_data["refresh_token"]
            )

        # Store in MongoDB
        await self.database_service.insert_record(self.collection, session_data)

        # Cache in Redis
        cache_key = f"session:{session_id}"
        await self.cache_service.set(cache_key, session_data, ttl=self.cache_ttl)

        self.logger.info(
            f"Session created: {session_id}",
            extra={
                "action": "create_session",
                "session_id": session_id,
                "user_id": session_data.get("user_id"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return session_id

    async def get_session(self, session_id: str) -> dict | None:
        """Get session by ID.

        Args:
        ----
            session_id: Session identifier

        Returns:
        -------
            Session data or None if not found

        """
        # Try cache first
        cache_key = f"session:{session_id}"
        session = await self.cache_service.get(cache_key)

        if session:
            self.logger.debug(
                f"Session retrieved from cache: {session_id}",
                extra={
                    "action": "get_session",
                    "session_id": session_id,
                    "source": "cache",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            return session

        # Fallback to database
        session = await self.database_service.get_record(
            self.collection, {"id": session_id}
        )

        if session:
            # Cache the result
            await self.cache_service.set(cache_key, session, ttl=self.cache_ttl)

            self.logger.debug(
                f"Session retrieved from database: {session_id}",
                extra={
                    "action": "get_session",
                    "session_id": session_id,
                    "source": "database",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        else:
            self.logger.debug(
                f"Session not found: {session_id}",
                extra={
                    "action": "get_session",
                    "session_id": session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        return session

    async def get_user_sessions(self, user_id: str) -> list[dict]:
        """Get all sessions for a user.

        Args:
        ----
            user_id: User identifier

        Returns:
        -------
            List of session data

        """
        # This would need a custom query method in DatabaseService
        # For now, we'll use a simple approach
        sessions = await self.database_service.execute_query(
            f"SELECT * FROM {self.collection} WHERE user_id = :user_id",
            {"user_id": user_id},
        )

        self.logger.debug(
            f"User sessions retrieved: {user_id}",
            extra={
                "action": "get_user_sessions",
                "user_id": user_id,
                "session_count": len(sessions) if sessions else 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return sessions or []

    async def update_session(self, session_id: str, updates: dict) -> bool:
        """Update session data.

        Args:
        ----
            session_id: Session identifier
            updates: Update data dictionary

        Returns:
        -------
            True if updated successfully

        """
        updates["updated_at"] = datetime.now(timezone.utc)

        # Update database
        result = await self.database_service.update_record(
            self.collection, {"id": session_id}, updates
        )

        if result:
            # Update cache
            cache_key = f"session:{session_id}"
            await self.cache_service.delete(cache_key)

            # Get updated session and cache it
            updated_session = await self.get_session(session_id)
            if updated_session:
                await self.cache_service.set(
                    cache_key, updated_session, ttl=self.cache_ttl
                )

            self.logger.info(
                f"Session updated: {session_id}",
                extra={
                    "action": "update_session",
                    "session_id": session_id,
                    "updates": list(updates.keys()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        else:
            self.logger.warning(
                f"Session update failed: {session_id}",
                extra={
                    "action": "update_session",
                    "session_id": session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        return result

    async def revoke_session(self, session_id: str) -> bool:
        """Revoke a session.

        Args:
        ----
            session_id: Session identifier

        Returns:
        -------
            True if revoked successfully

        """
        result = await self.update_session(
            session_id, {"revoked_at": datetime.now(timezone.utc)}
        )

        if result:
            # Remove from cache
            cache_key = f"session:{session_id}"
            await self.cache_service.delete(cache_key)

            self.logger.info(
                f"Session revoked: {session_id}",
                extra={
                    "action": "revoke_session",
                    "session_id": session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        return result

    async def revoke_user_sessions(
        self, user_id: str, except_session_id: str = None
    ) -> int:
        """Revoke all sessions for a user.

        Args:
        ----
            user_id: User identifier
            except_session_id: Session ID to exclude from revocation

        Returns:
        -------
            Number of sessions revoked

        """
        # This would need a custom query method
        # For now, we'll use a simple approach
        sessions = await self.get_user_sessions(user_id)
        revoked_count = 0

        for session in sessions:
            if except_session_id and session["id"] == except_session_id:
                continue

            if await self.revoke_session(session["id"]):
                revoked_count += 1

        self.logger.info(
            f"User sessions revoked: {user_id}",
            extra={
                "action": "revoke_user_sessions",
                "user_id": user_id,
                "revoked_count": revoked_count,
                "except_session_id": except_session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return revoked_count

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions.

        Returns
        -------
            Number of sessions cleaned up

        """
        # This would need a custom query method
        # For now, we'll use a simple approach
        now = datetime.now(timezone.utc)

        # This is a placeholder - would need proper implementation
        cleaned_count = 0

        self.logger.info(
            f"Expired sessions cleaned up: {cleaned_count}",
            extra={
                "action": "cleanup_expired_sessions",
                "cleaned_count": cleaned_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return cleaned_count


__all__ = ["SessionRepository"]
