"""Session management functionality for authentication."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.interfaces.session_repository_interface import (
        SessionRepositoryInterface,
    )
    from app.models.session import DeviceInfo
    from app.services.logger import Logger


class SessionManagementMixin:
    """Session management functionality mixin."""

    def __init__(
        self: SessionManagementMixin,
        logger: Logger,
        session_repository: SessionRepositoryInterface = None,
    ) -> None:
        """Initialize session management mixin.

        Args:
        ----
            logger: The logger to use.
            session_repository: Session repository interface.

        Returns:
        -------
            None

        """
        self.logger = logger
        self.session_repository = session_repository

    async def create_session(
        self: SessionManagementMixin, user_id: str, device_info: DeviceInfo
    ) -> str:
        """Create a new session.

        Args:
        ----
            user_id: User ID.
            device_info: Device information.

        Returns:
        -------
            Session ID.

        """
        if not self.session_repository:
            raise ValueError("Session repository required")

        session_data = {
            "user_id": user_id,
            "device_info": device_info.dict(),
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc).timestamp()
            + (7 * 24 * 60 * 60),  # 7 days
            "revoked_at": None,
        }

        session_id = await self.session_repository.create_session(session_data)

        if session_id:
            self.logger.info(
                "Session created",
                extra={
                    "service": "SessionManagementMixin",
                    "user_id": user_id,
                    "session_id": session_id,
                    "device_info": device_info.dict(),
                },
            )
        else:
            self.logger.error(
                "Failed to create session",
                extra={
                    "service": "SessionManagementMixin",
                    "user_id": user_id,
                },
            )

        return session_id

    async def get_session(self: SessionManagementMixin, session_id: str) -> dict | None:
        """Get session by ID.

        Args:
        ----
            session_id: Session ID.

        Returns:
        -------
            Session data if found, None otherwise.

        """
        if not self.session_repository:
            return None

        session_data = await self.session_repository.get_session(session_id)

        if session_data:
            self.logger.debug(
                "Session retrieved",
                extra={
                    "service": "SessionManagementMixin",
                    "session_id": session_id,
                },
            )
        else:
            self.logger.debug(
                "Session not found",
                extra={
                    "service": "SessionManagementMixin",
                    "session_id": session_id,
                },
            )

        return session_data

    async def revoke_session(self: SessionManagementMixin, session_id: str) -> bool:
        """Revoke a session.

        Args:
        ----
            session_id: Session ID.

        Returns:
        -------
            True if revoked successfully, False otherwise.

        """
        if not self.session_repository:
            return False

        success = await self.session_repository.revoke_session(session_id)

        if success:
            self.logger.info(
                "Session revoked",
                extra={
                    "service": "SessionManagementMixin",
                    "session_id": session_id,
                },
            )
        else:
            self.logger.warning(
                "Failed to revoke session",
                extra={
                    "service": "SessionManagementMixin",
                    "session_id": session_id,
                },
            )

        return success

    async def revoke_user_sessions(
        self: SessionManagementMixin, user_id: str, except_session_id: str | None = None
    ) -> int:
        """Revoke all user sessions except specified one.

        Args:
        ----
            user_id: User ID.
            except_session_id: Session ID to exclude from revocation.

        Returns:
        -------
            Number of sessions revoked.

        """
        if not self.session_repository:
            return 0

        count = await self.session_repository.revoke_user_sessions(
            user_id, except_session_id
        )

        self.logger.info(
            "User sessions revoked",
            extra={
                "service": "SessionManagementMixin",
                "user_id": user_id,
                "count": count,
                "except_session_id": except_session_id,
            },
        )

        return count

    async def cleanup_expired_sessions(self: SessionManagementMixin) -> int:
        """Cleanup expired sessions.

        Returns
        -------
            Number of sessions cleaned up.

        """
        if not self.session_repository:
            return 0

        count = await self.session_repository.cleanup_expired_sessions()

        if count > 0:
            self.logger.info(
                "Expired sessions cleaned up",
                extra={
                    "service": "SessionManagementMixin",
                    "count": count,
                },
            )

        return count

    def _verify_device_fingerprint(
        self: SessionManagementMixin, session_data: dict, device_info: DeviceInfo
    ) -> bool:
        """Verify device fingerprint matches session.

        Args:
        ----
            session_data: Session data.
            device_info: Current device info.

        Returns:
        -------
            True if fingerprint matches, False otherwise.

        """
        if not session_data or "device_info" not in session_data:
            return False

        stored_device_info = session_data["device_info"]

        # Simple fingerprint comparison (in production, use more sophisticated method)
        current_fingerprint = f"{device_info.ip_address}:{device_info.user_agent[:50]}"
        stored_ip = stored_device_info.get("ip_address", "")
        stored_ua = stored_device_info.get("user_agent", "")
        stored_fingerprint = f"{stored_ip}:{stored_ua[:50]}"

        match = current_fingerprint == stored_fingerprint

        if not match:
            self.logger.warning(
                "Device fingerprint mismatch",
                extra={
                    "service": "SessionManagementMixin",
                    "session_id": session_data.get("id"),
                    "current_fingerprint": current_fingerprint,
                    "stored_fingerprint": stored_fingerprint,
                },
            )

        return match
