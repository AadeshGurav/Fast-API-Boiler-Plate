"""Session repository interface for platform-agnostic session operations."""
from __future__ import annotations

from abc import abstractmethod

from app.core.interfaces.base_interface import BaseInterface


class SessionRepositoryInterface(BaseInterface):
    """Interface for session repository operations."""

    @abstractmethod
    async def create_session(self, session_data: dict) -> str:
        """Create a new session.

        Args:
            session_data: Session data dictionary

        Returns:
            Session ID

        """
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> dict | None:
        """Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session data or None if not found

        """
        pass

    @abstractmethod
    async def get_user_sessions(self, user_id: str) -> list[dict]:
        """Get all sessions for a user.

        Args:
            user_id: User identifier

        Returns:
            List of session data

        """
        pass

    @abstractmethod
    async def update_session(self, session_id: str, updates: dict) -> bool:
        """Update session data.

        Args:
            session_id: Session identifier
            updates: Update data dictionary

        Returns:
            True if updated successfully

        """
        pass

    @abstractmethod
    async def revoke_session(self, session_id: str) -> bool:
        """Revoke a session.

        Args:
            session_id: Session identifier

        Returns:
            True if revoked successfully

        """
        pass

    @abstractmethod
    async def revoke_user_sessions(
        self, user_id: str, except_session_id: str = None
    ) -> int:
        """Revoke all sessions for a user.

        Args:
            user_id: User identifier
            except_session_id: Session ID to exclude from revocation

        Returns:
            Number of sessions revoked

        """
        pass

    @abstractmethod
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions.

        Returns:
            Number of sessions cleaned up

        """
        pass


__all__ = ["SessionRepositoryInterface"]
