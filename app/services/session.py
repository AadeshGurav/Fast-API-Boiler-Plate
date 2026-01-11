"""Session management service using DataService (cache) with logging."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from app.services.base_service import BaseService

if TYPE_CHECKING:
    from app.services.data import DataService
    from app.services.logger import Logger
    from config import Config


class SessionService(BaseService):
    """Service for managing sessions using cache backend (DataService).

    Features:
    - Create, get, update, delete sessions
    - Session TTL management
    - Logging for all operations
    """

    def __init__(
        self: SessionService,
        config: Config,
        logger: Logger,
        data_service: DataService,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize the SessionService.

        Args:
        ----
            config: The configuration to use.
            logger: The logger to use.
            data_service: The data service to use.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
        -------
            None

        """
        super().__init__(config, logger, *args, **kwargs)
        self.data_service: DataService = data_service
        self.session_ttl: int = self.config.get("session_ttl", 3600)
        self.logger.info(
            "SessionService initialized", extra={"service": "SessionService"}
        )

    async def create_session(
        self: SessionService, data: dict[str, Any] | None = None
    ) -> str:
        """Create a new session and store it in cache.

        Args:
        ----
            data: Optional initial session data.

        Returns:
        -------
            The generated session ID.

        """
        session_id = str(uuid.uuid4())
        session_data = data or {}
        session_data["id"] = session_id

        await self.data_service.sessions.create_session(session_data)
        self.logger.debug(f"Created session '{session_id}' with TTL={self.session_ttl}")
        return session_id

    async def get_session(
        self: SessionService, session_id: str
    ) -> dict[str, Any] | None:
        """Retrieve session data by session ID.

        Args:
        ----
            session_id: Session ID to retrieve.

        Returns:
        -------
            The session data if exists, otherwise None.

        """
        data = await self.data_service.sessions.get_session(session_id)
        if data is None:
            self.logger.debug(f"Session not found: '{session_id}'")
        return data

    async def update_session(
        self: SessionService, session_id: str, data: dict[str, Any]
    ) -> bool:
        """Update an existing session with new data.

        Args:
        ----
            session_id: Session ID to update.
            data: Data to merge/update.

        Returns:
        -------
            True if session was updated, False if session does not exist.

        """
        result = await self.data_service.sessions.update_session(session_id, data)
        if result:
            self.logger.debug(
                f"Updated session '{session_id}' with TTL={self.session_ttl}"
            )
        else:
            self.logger.warning(
                f"Attempted to update non-existent session '{session_id}'"
            )
        return result

    async def delete_session(self: SessionService, session_id: str) -> bool:
        """Delete a session by session ID.

        Args:
        ----
            session_id: Session ID to delete.

        Returns:
        -------
            True if the session was deleted, False otherwise.

        """
        result = await self.data_service.sessions.revoke_session(session_id)
        if result:
            self.logger.debug(f"Deleted session '{session_id}'")
        else:
            self.logger.debug(
                f"Attempted to delete non-existent session '{session_id}'"
            )
        return result

    async def extend_session(self: SessionService, session_id: str) -> bool:
        """Extend the TTL of an existing session.

        Args:
        ----
            session_id: Session ID to extend.

        Returns:
        -------
            True if TTL was extended, False otherwise.

        """
        # Extend session by updating expires_at
        from datetime import datetime, timezone

        result = await self.data_service.sessions.update_session(
            session_id,
            {
                "expires_at": datetime.now(timezone.utc).timestamp() + self.session_ttl,
            },
        )

        if result:
            self.logger.debug(f"Extended session '{session_id}' TTL={self.session_ttl}")
        else:
            self.logger.warning(f"Failed to extend non-existent session '{session_id}'")

        return result
