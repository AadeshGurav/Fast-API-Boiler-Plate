"""Session management functionality for authentication.

The ``sessions`` collection is the only source of truth for sessions. Access and
refresh tokens carry the session id (``sid``), so revoking a session invalidates
every token issued for it.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from app.services.data.sessions_ops import is_session_active

if TYPE_CHECKING:
    from app.models.session import DeviceInfo
    from app.models.user import User
    from app.services.data import DataService
    from app.services.logger import Logger


class SessionManager:
    """Creates, looks up and revokes server-side sessions."""

    def __init__(
        self,
        logger: Logger,
        data_service: DataService | None = None,
        refresh_days: int = 7,
        remember_me_days: int = 30,
    ) -> None:
        """Initialize session management mixin.

        Args:
        ----
            logger: The logger to use.
            data_service: Data service instance.

        """
        self.logger = logger
        self.data_service = data_service
        self.refresh_days = refresh_days
        self.remember_me_days = remember_me_days

    async def create_session(
        self,
        user: User,
        device_info: DeviceInfo,
        remember_me: bool = False,
        *,
        session_id: str | None = None,
        refresh_token: str | None = None,
    ) -> str:
        """Create a session.

        Args:
        ----
            user: Session owner.
            device_info: Device information.
            remember_me: If True, the session lasts 30 days instead of 7.
            session_id: Pre-generated id, so tokens can be signed with it first.
            refresh_token: The session's current refresh token (stored hashed).

        Returns:
        -------
            Session ID.

        Raises:
        ------
            ValueError: If there is no data service or the session was not stored.

        """
        if not self.data_service:
            raise ValueError("Data service required")

        now = datetime.now(UTC)
        days = self.remember_me_days if remember_me else self.refresh_days
        session_data = {
            "id": session_id or uuid.uuid4().hex,
            "user_id": user.id,
            "device_info": device_info.model_dump(),
            "created_at": now,
            "last_used_at": now,
            "expires_at": now + timedelta(days=days),
            "revoked_at": None,
        }
        if refresh_token:
            session_data["refresh_token"] = refresh_token

        created_id = await self.data_service.sessions.create_session(session_data)
        if not created_id:
            self.logger.error(
                "Failed to create session",
                extra={"service": "SessionManager", "user_id": user.id},
            )
            raise ValueError("Failed to create session")

        self.logger.info(
            "Session created",
            extra={
                "service": "SessionManager",
                "user_id": user.id,
                "session_id": created_id,
            },
        )
        return created_id

    async def get_session(self, session_id: str) -> dict | None:
        """Get session by ID (None if unknown)."""
        if not self.data_service:
            return None
        return await self.data_service.sessions.get_session(session_id)

    async def is_session_active(self, session_id: str | None) -> bool:
        """Whether the session exists, is not revoked and has not expired."""
        if not session_id:
            return False
        return is_session_active(await self.get_session(session_id))

    async def revoke_session(self, session_id: str) -> bool:
        """Revoke a session; every token issued for it stops working.

        Returns:
        -------
            True if the session existed and was revoked.

        """
        if not self.data_service:
            return False

        success = await self.data_service.sessions.revoke_session(session_id)
        extra = {"service": "SessionManager", "session_id": session_id}
        if success:
            self.logger.info("Session revoked", extra=extra)
        else:
            self.logger.warning("Failed to revoke session", extra=extra)
        return success

    async def revoke_user_sessions(self, user_id: str, except_session_id: str | None = None) -> int:
        """Revoke all of a user's sessions, optionally keeping one.

        Returns:
        -------
            Number of sessions revoked.

        """
        if not self.data_service:
            return 0

        count = await self.data_service.sessions.revoke_user_sessions(user_id, except_session_id)
        self.logger.info(
            "User sessions revoked",
            extra={
                "service": "SessionManager",
                "user_id": user_id,
                "count": count,
                "except_session_id": except_session_id,
            },
        )
        return count
