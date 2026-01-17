from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from fastapi import Request, Response

from app.models.session import DeviceInfo
from app.services.data import DataService

from .base import BaseMiddleware


class SessionMiddleware(BaseMiddleware):
    """Enhanced session middleware using DataService with device tracking."""

    def initialize(
        self: SessionMiddleware,
        data_service: DataService,
        **kwargs,
    ) -> None:
        """Initialize the enhanced SessionMiddleware.

        Args:
        ----
            cache_service: The cache service instance.
            database_service: The database service instance.
            kwargs: Additional keyword arguments.

        """
        self.data_service: DataService = data_service
        self.cookie_name = self.config.get("auth_session_cookie_name", "auth_session")
        self.max_age = self.config.get(
            "session_max_age", 7 * 24 * 60 * 60
        )  # 7 days to match JWT refresh token
        self.path = self.config.get("session_cookie_path", "/")
        self.same_site = self.config.get("session_cookie_same_site", "lax")
        # Cookie security settings (default to False for development/HTTP)
        self.httponly = self.config.get("cookie_httponly", False)
        self.secure = self.config.get("cookie_secure", False)
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
            },
        )

    async def process_request(
        self: SessionMiddleware, request: Request, call_next: Callable
    ) -> Response:
        """Process the request using DataService with device tracking.

        Only processes sessions for authenticated users. Unauthenticated requests
        bypass session management.

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

        # Check if user is authenticated by looking for JWT token
        # This is checked before session management since sessions are only for authenticated users
        from app.utils.permissions import _extract_token_from_request

        token = _extract_token_from_request(request)
        session_id = None
        session_data = None

        # Only manage sessions for authenticated users
        if token and self.data_service:
            session_id = request.cookies.get(self.cookie_name)

            if session_id:
                try:
                    # Get session from DataService (hybrid MongoDB + Redis)
                    session_data = await self.data_service.sessions.get_session(
                        session_id
                    )

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
                            await self._update_session_device_info(
                                session_id, device_info
                            )

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

            # Note: We don't create sessions here - they're created by AuthService during login
            # Session cookie is set by AuthService.login_user(), not middleware

        # Store session in request state (may be None for unauthenticated requests)
        request.state.session = session_data or {}
        if session_id:
            request.state.session_id = session_id

        # Process the request
        response = await call_next(request)

        # Only set/update session cookie if we have a session_id
        # (cookie is primarily set during login by AuthService)
        if session_id:
            self._set_cookie(response, session_id)

        # Set refreshed tokens in cookies if they were refreshed
        if hasattr(request.state, "token_refreshed") and request.state.token_refreshed:
            from app.models.auth import TokenPair
            from app.utils.cookie_manager import CookieManager

            access_token = (
                request.state.new_access_token
                if hasattr(request.state, "new_access_token")
                else None
            )
            refresh_token = (
                request.state.new_refresh_token
                if hasattr(request.state, "new_refresh_token")
                else None
            )
            expires_in = (
                request.state.token_expires_in
                if hasattr(request.state, "token_expires_in")
                else 3600
            )

            if access_token and refresh_token:
                token_pair = TokenPair(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_in=expires_in,
                )
                # Check if remember_me was preserved from refresh
                remember_me = getattr(request.state, "remember_me", False)
                CookieManager.set_auth_cookies(
                    response, token_pair, self.config, remember_me
                )

            self.logger.info(
                "Tokens refreshed and set in cookies",
                extra={
                    "middleware": "SessionMiddleware",
                    "action": "token_refresh",
                    "path": request.url.path,
                },
            )

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
        response.set_cookie(
            key=self.cookie_name,
            value=session_id,
            max_age=self.max_age,
            path=self.path,
            httponly=self.httponly,
            secure=self.secure,
            samesite=self.same_site,
        )

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
        if not self.data_service:
            return

        try:
            await self.data_service.sessions.update_session(
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
        if not self.data_service:
            return

        try:
            await self.data_service.sessions.update_session(
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
