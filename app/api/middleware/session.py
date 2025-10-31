from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Request, Response
from starlette.datastructures import MutableHeaders

from app.core.interfaces.session_repository_interface import SessionRepositoryInterface
from app.database.repositories.session_repository import SessionRepository
from app.models.session import DeviceInfo
from app.services.cache import CacheService
from app.services.database_service import DatabaseService

from .base import BaseMiddleware


class SessionMiddleware(BaseMiddleware):
    """Enhanced session middleware using session repository with device tracking."""

    def initialize(
        self: SessionMiddleware,
        cache_service: CacheService,
        database_service: DatabaseService,
        **kwargs,
    ) -> None:
        """Initialize the enhanced SessionMiddleware.

        Args:
        ----
            cache_service: The cache service instance.
            database_service: The database service instance.
            kwargs: Additional keyword arguments.

        """
        self.session_repository: SessionRepositoryInterface = SessionRepository(
            cache_service,
            database_service,
            self.logger,
        )
        self.cookie_name = self.config.get("session_cookie_name", "session")
        self.max_age = self.config.get("session_max_age", 14 * 24 * 60 * 60)
        self.path = self.config.get("session_cookie_path", "/")
        self.same_site = self.config.get("session_cookie_same_site", "lax")
        self.https_only = self.config.get("session_cookie_https_only", False)
        self.extend_on_activity = self.config.get("extend_on_activity", True)
        self.track_device_info = self.config.get("track_device_info", True)

        self.logger.info(
            "Enhanced SessionMiddleware initialized",
            extra={
                "middleware": "SessionMiddleware",
                "cookie_name": self.cookie_name,
                "max_age": self.max_age,
                "extend_on_activity": self.extend_on_activity,
                "track_device_info": self.track_device_info,
                "session_repository_available": self.session_repository is not None,
            },
        )

    async def process_request(
        self: SessionMiddleware, request: Request, call_next: Callable
    ) -> Response:
        """Process the request using session repository with device tracking.

        Args:
        ----
            request: The request to process.
            call_next: The next middleware to call.

        Returns:
        -------
            The response to return.

        """
        self.logger.debug(
            f"Processing request: {request.method} {request.url.path}",
            extra={
                "middleware": "SessionMiddleware",
                "action": "process_request",
                "path": request.url.path,
                "method": request.method,
            },
        )

        session_id = request.cookies.get(self.cookie_name)
        session_data = None

        if session_id and self.session_repository:
            try:
                # Get session from repository (hybrid MongoDB + Redis)
                session_data = await self.session_repository.get_session(session_id)

                if session_data:
                    self.logger.debug(
                        f"Loaded existing session: {session_id}",
                        extra={
                            "middleware": "SessionMiddleware",
                            "action": "session_load",
                            "session_id": session_id,
                            "user_id": session_data.get("user_id"),
                        },
                    )

                    # Track device info if enabled
                    if self.track_device_info:
                        device_info = self._extract_device_info(request)
                        await self._update_session_device_info(session_id, device_info)

                    # Extend session on activity if enabled
                    if self.extend_on_activity:
                        await self._extend_session_on_activity(session_id)
                else:
                    self.logger.debug(
                        f"Session not found: {session_id}",
                        extra={
                            "middleware": "SessionMiddleware",
                            "action": "session_not_found",
                            "session_id": session_id,
                        },
                    )
                    session_id = None

            except Exception as e:  # noqa: BLE001
                self.logger.error(
                    f"Error loading session: {str(e)}",
                    extra={
                        "middleware": "SessionMiddleware",
                        "action": "session_load_error",
                        "session_id": session_id,
                        "error": str(e),
                    },
                )
                session_id = None

        # Create new session if none exists
        if not session_id:
            session_id = str(uuid4())
            session_data = {
                "created_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc).timestamp() + self.max_age,
            }

            if self.track_device_info:
                device_info = self._extract_device_info(request)
                session_data["device_info"] = device_info.dict()

            # Store new session in repository
            if self.session_repository:
                try:
                    await self.session_repository.create_session(session_data)
                    self.logger.info(
                        f"Created new session: {session_id}",
                        extra={
                            "middleware": "SessionMiddleware",
                            "action": "session_create",
                            "session_id": session_id,
                            "device_info": session_data.get("device_info"),
                        },
                    )
                except Exception as e:  # noqa: BLE001
                    self.logger.error(
                        f"Error creating session: {str(e)}",
                        extra={
                            "middleware": "SessionMiddleware",
                            "action": "session_create_error",
                            "session_id": session_id,
                            "error": str(e),
                        },
                    )

        # Store session in request state
        request.state.session = session_data or {}
        request.state.session_id = session_id

        # Process the request
        response = await call_next(request)

        # Set session cookie
        self._set_cookie(response, session_id)

        self.logger.debug(
            f"Completed request processing: {request.method} {request.url.path}",
            extra={
                "middleware": "SessionMiddleware",
                "action": "request_complete",
                "path": request.url.path,
                "method": request.method,
                "session_id": session_id,
            },
        )

        return response

    def _set_cookie(
        self: SessionMiddleware, response: Response, session_id: str
    ) -> None:
        """Set the session cookie in the response.

        Args:
        ----
            response: The response to set the cookie in.
            session_id: The session ID to set the cookie for.

        """
        headers = MutableHeaders(response.headers)

        cookie = f"{self.cookie_name}={session_id}; Path={self.path}; Max-Age={self.max_age}; SameSite={self.same_site}"  # noqa

        if self.https_only:
            cookie += "; Secure"

        headers.append("Set-Cookie", cookie)

        self.logger.debug(
            f"Set cookie headers for session: {session_id}",
            extra={
                "middleware": "SessionMiddleware",
                "action": "set_cookie",
                "session_id": session_id,
            },
        )

    async def _update_session_device_info(
        self: SessionMiddleware, session_id: str, device_info: DeviceInfo
    ) -> None:
        """Update session with device information.

        Args:
        ----
            session_id: The session ID.
            device_info: The device information.

        """
        if not self.session_repository:
            return

        try:
            await self.session_repository.update_session(
                session_id,
                {
                    "device_info": device_info.dict(),
                    "last_used_at": datetime.now(timezone.utc),
                },
            )

            self.logger.debug(
                f"Updated session device info: {session_id}",
                extra={
                    "middleware": "SessionMiddleware",
                    "action": "update_device_info",
                    "session_id": session_id,
                    "device_info": device_info.dict(),
                },
            )
        except Exception as e:  # noqa: BLE001
            self.logger.error(
                f"Error updating session device info: {str(e)}",
                extra={
                    "middleware": "SessionMiddleware",
                    "action": "update_device_info_error",
                    "session_id": session_id,
                    "error": str(e),
                },
            )

    async def _extend_session_on_activity(
        self: SessionMiddleware, session_id: str
    ) -> None:
        """Extend session expiration on activity.

        Args:
        ----
            session_id: The session ID.

        """
        if not self.session_repository:
            return

        try:
            await self.session_repository.update_session(
                session_id,
                {
                    "last_used_at": datetime.now(timezone.utc),
                    "expires_at": datetime.now(timezone.utc).timestamp() + self.max_age,
                },
            )

            self.logger.debug(
                f"Extended session on activity: {session_id}",
                extra={
                    "middleware": "SessionMiddleware",
                    "action": "extend_session",
                    "session_id": session_id,
                },
            )
        except Exception as e:  # noqa: BLE001
            self.logger.error(
                f"Error extending session: {str(e)}",
                extra={
                    "middleware": "SessionMiddleware",
                    "action": "extend_session_error",
                    "session_id": session_id,
                    "error": str(e),
                },
            )
