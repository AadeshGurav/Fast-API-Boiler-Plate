"""Session management functionality for authentication."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.session import DeviceInfo
    from app.services.data import DataService
    from app.services.logger import Logger


class SessionManagementMixin:
    """Session management functionality mixin."""

    def __init__(
        self: SessionManagementMixin,
        logger: Logger,
        data_service: DataService = None,
    ) -> None:
        """Initialize session management mixin.

        Args:
        ----
            logger: The logger to use.
            data_service: Data service instance.

        Returns:
        -------
            None

        """
        self.logger = logger
        self.data_service = data_service

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
        if not self.data_service:
            raise ValueError("Data service required")

        session_data = {
            "user_id": user_id,
            "device_info": device_info.dict(),
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc).timestamp()
            + (7 * 24 * 60 * 60),  # 7 days
            "revoked_at": None,
        }

        session_id = await self.data_service.sessions.create_session(session_data)

        if session_id:
            # Add session reference to user object if method is available
            # (e.g., when used in AuthService which has both mixins)
            if hasattr(self, "_add_session_to_user"):
                try:
                    await self._add_session_to_user(
                        user_id=user_id,
                        session_id=session_id,
                        device_info=device_info.dict(),
                        created_at=session_data["created_at"],
                        expires_at=session_data["expires_at"],
                    )
                except Exception as e:  # noqa: BLE001
                    self.logger.warning(
                        "Failed to add session to user",
                        extra={
                            "service": "SessionManagementMixin",
                            "user_id": user_id,
                            "session_id": session_id,
                            "error": str(e),
                        },
                    )

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
        if not self.data_service:
            return None

        session_data = await self.data_service.sessions.get_session(session_id)

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
        if not self.data_service:
            return False

        # Get session data to find user_id before revoking
        session_data = await self.data_service.sessions.get_session(session_id)
        user_id = session_data.get("user_id") if session_data else None

        success = await self.data_service.sessions.revoke_session(session_id)

        if success:
            # Update session reference in user object if method is available
            if user_id and hasattr(self, "_update_user_session"):
                try:
                    await self._update_user_session(user_id, session_id, revoked=True)
                except Exception as e:  # noqa: BLE001
                    self.logger.warning(
                        "Failed to update user session",
                        extra={
                            "service": "SessionManagementMixin",
                            "user_id": user_id,
                            "session_id": session_id,
                            "error": str(e),
                        },
                    )

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
        if not self.data_service:
            return 0

        count = await self.data_service.sessions.revoke_user_sessions(
            user_id, except_session_id
        )

        # Update all session references in user object if method is available
        if hasattr(self, "_update_user_sessions"):
            try:
                await self._update_user_sessions(user_id, except_session_id)
            except Exception as e:  # noqa: BLE001
                self.logger.warning(
                    "Failed to update user sessions",
                    extra={
                        "service": "SessionManagementMixin",
                        "user_id": user_id,
                        "error": str(e),
                    },
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
        if not self.data_service:
            return 0

        # Note: cleanup_expired_sessions is not implemented in ops yet
        # This would need to be added to sessions_ops if needed
        count = 0

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
