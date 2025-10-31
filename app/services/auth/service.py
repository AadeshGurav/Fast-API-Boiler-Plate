"""Main authentication service combining all auth mixins."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.interfaces.auth_service_interface import AuthServiceInterface
from app.models.auth import LoginResponse
from app.models.user import UserPublic
from app.services.auth.core import AuthCoreMixin
from app.services.auth.session_management import SessionManagementMixin
from app.services.auth.user_management import UserManagementMixin

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.core.interfaces.password_service_interface import PasswordServiceInterface
    from app.core.interfaces.rbac_service_interface import RBACServiceInterface
    from app.core.interfaces.session_repository_interface import (
        SessionRepositoryInterface,
    )
    from app.core.interfaces.user_repository_interface import UserRepositoryInterface
    from app.models.auth import TokenPair
    from app.models.session import DeviceInfo
    from app.models.user import UserCreate
    from app.services.logger import Logger
    from config import Config


class AuthService(
    AuthServiceInterface,
    AuthCoreMixin,
    UserManagementMixin,
    SessionManagementMixin,
):
    """Main authentication service combining all auth functionality."""

    def __init__(
        self: AuthService,
        logger: Logger,
        config: Config,
        session_repository: SessionRepositoryInterface = None,
        user_repository: UserRepositoryInterface = None,
        password_service: PasswordServiceInterface = None,
        rbac_service: RBACServiceInterface = None,
    ) -> None:
        """Initialize authentication service.

        Args:
        ----
            logger: The logger to use.
            config: The configuration to use.
            session_repository: Session repository interface.
            user_repository: User repository interface.
            password_service: Password service interface.
            rbac_service: RBAC service interface.

        """
        # Initialize all mixins
        AuthCoreMixin.__init__(
            self,
            logger,
            config,
            session_repository,
            user_repository,
            password_service,
            rbac_service,
        )
        UserManagementMixin.__init__(self, logger, user_repository, password_service)
        SessionManagementMixin.__init__(self, logger, session_repository)

    # Interface implementation methods
    def create_tokens(
        self: AuthService, data: dict[str, Any], user_role: str = "user"
    ) -> tuple[str, str]:
        """Create both access and refresh tokens with role information.

        Args:
        ----
            data: Token data containing user information.
            user_role: User role for token.

        Returns:
        -------
            Tuple of (access_token, refresh_token).

        """
        user_id = data.get("user_id", "")
        username = data.get("username", "")
        roles = data.get("roles", [user_role])
        permissions = data.get("permissions", [])

        access_token = self.create_access_token(user_id, username, roles, permissions)
        refresh_token = self.create_refresh_token(user_id)

        return access_token, refresh_token

    def create_access_token(self: AuthService, data: dict[str, Any]) -> str:
        """Create a JWT access token.

        Args:
        ----
            data: Token data containing user information.

        Returns:
        -------
            JWT access token.

        """
        user_id = data.get("user_id", "")
        username = data.get("username", "")
        roles = data.get("roles", [])
        permissions = data.get("permissions", [])

        return self.create_access_token(user_id, username, roles, permissions)

    def create_refresh_token(self: AuthService, data: dict[str, Any]) -> str:
        """Create a JWT refresh token.

        Args:
        ----
            data: Token data containing user information.

        Returns:
        -------
            JWT refresh token.

        """
        user_id = data.get("user_id", "")
        return self.create_refresh_token(user_id)

    def decode_token(
        self: AuthService, token: str, verify_type: str | None = None
    ) -> dict[str, Any]:
        """Decode and validate a JWT token.

        Args:
        ----
            token: JWT token to decode.
            verify_type: Token type to verify (access/refresh).

        Returns:
        -------
            Decoded token payload as dictionary.

        """
        token_payload = self.verify_token(token, verify_type)
        if not token_payload:
            return {}

        return token_payload.dict()

    async def get_current_user(
        self: AuthService, access_token: str = None
    ) -> dict[str, Any]:
        """Get the current user from the access token.

        Args:
        ----
            access_token: JWT access token.

        Returns:
        -------
            Current user data.

        """
        if not access_token:
            return {}

        token_payload = self.verify_token(access_token, "access")
        if not token_payload:
            return {}

        user_data = await self.get_user_by_id(token_payload.user_id)
        if not user_data:
            return {}

        return user_data.dict()

    async def is_admin(self: AuthService, current_user: dict[str, Any]) -> bool:
        """Check if the current user is an admin.

        Args:
        ----
            current_user: Current user data.

        Returns:
        -------
            True if user is admin, False otherwise.

        """
        roles = current_user.get("roles", [])
        return "admin" in roles

    def admin_required(self: AuthService, func: Callable) -> Callable:
        """Decorator to require admin role for a route.

        Args:
        ----
            func: Function to decorate.

        Returns:
        -------
            Decorated function.

        """
        # This would be implemented as a FastAPI dependency
        # For now, return the function as-is
        return func

    def login(self: AuthService, user: Any) -> Any:
        """Log user login event.

        Args:
        ----
            user: The user to log in.

        """
        self.logger.info(
            "User login event",
            extra={
                "service": "AuthService",
                "user_id": getattr(user, "id", None),
                "username": getattr(user, "username", None),
            },
        )

    # Additional methods from original plan
    async def register_user(self: AuthService, user_data: UserCreate) -> UserPublic:
        """Register a new user.

        Args:
        ----
            user_data: User creation data.

        Returns:
        -------
            Created user (public data).

        """
        return await UserManagementMixin.register_user(self, user_data)

    async def login_user(
        self: AuthService, username: str, password: str, device_info: DeviceInfo
    ) -> LoginResponse:
        """Login user with username and password.

        Args:
        ----
            username: Username.
            password: Password.
            device_info: Device information.

        Returns:
        -------
            Login response with user, tokens, and permissions.

        """
        # Get user by username
        user = await self.get_user_by_username(username)
        if not user:
            self.logger.warning(
                "Login attempt with non-existent username",
                extra={
                    "service": "AuthService",
                    "username": username,
                },
            )
            raise ValueError("Invalid credentials")

        # Verify password
        if not self.password_service.verify_password(password, user.password_hash):
            self.logger.warning(
                "Login attempt with invalid password",
                extra={
                    "service": "AuthService",
                    "username": username,
                    "user_id": user.id,
                },
            )
            raise ValueError("Invalid credentials")

        # Resolve user permissions
        permissions = await self.rbac_service.resolve_user_permissions(user.id)

        # Create session
        session_id = await self.create_session(user.id, device_info)

        # Create tokens
        token_pair = self.create_token_pair(
            user.id, user.username, user.roles, permissions
        )

        # Log successful login
        self.logger.info(
            "User logged in successfully",
            extra={
                "service": "AuthService",
                "user_id": user.id,
                "username": username,
                "session_id": session_id,
                "device_info": device_info.dict(),
            },
        )

        return LoginResponse(
            user=UserPublic(**user.dict()),
            tokens=token_pair,
            permissions=permissions,
        )

    async def refresh_tokens(
        self: AuthService, refresh_token: str, device_info: DeviceInfo
    ) -> TokenPair:
        """Refresh access and refresh tokens.

        Args:
        ----
            refresh_token: Current refresh token.
            device_info: Device information.

        Returns:
        -------
            New token pair.

        """
        # Verify refresh token
        token_payload = self.verify_token(refresh_token, "refresh")
        if not token_payload:
            raise ValueError("Invalid refresh token")

        # Get user
        user = await self.get_user_by_id(token_payload.user_id)
        if not user:
            raise ValueError("User not found")

        # Resolve permissions
        permissions = await self.rbac_service.resolve_user_permissions(user.id)

        # Create new token pair
        new_token_pair = self.create_token_pair(
            user.id, user.username, user.roles, permissions
        )

        # Log token refresh
        self.logger.info(
            "Tokens refreshed",
            extra={
                "service": "AuthService",
                "user_id": user.id,
                "username": user.username,
            },
        )

        return new_token_pair

    async def logout(self: AuthService, session_id: str) -> bool:
        """Logout user by revoking session.

        Args:
        ----
            session_id: Session ID to revoke.

        Returns:
        -------
            True if logout successful, False otherwise.

        """
        success = await self.revoke_session(session_id)

        if success:
            self.logger.info(
                "User logged out",
                extra={
                    "service": "AuthService",
                    "session_id": session_id,
                },
            )

        return success

    async def logout_all_devices(
        self: AuthService, user_id: str, except_session_id: str = None
    ) -> int:
        """Logout user from all devices except specified session.

        Args:
        ----
            user_id: User ID.
            except_session_id: Session ID to exclude from logout.

        Returns:
        -------
            Number of sessions revoked.

        """
        count = await self.revoke_user_sessions(user_id, except_session_id)

        self.logger.info(
            "All sessions revoked",
            extra={
                "service": "AuthService",
                "user_id": user_id,
                "count": count,
                "except_session_id": except_session_id,
            },
        )

        return count

    async def verify_device_fingerprint(
        self: AuthService, session_id: str, device_info: DeviceInfo
    ) -> bool:
        """Verify device fingerprint matches session.

        Args:
        ----
            session_id: Session ID.
            device_info: Current device info.

        Returns:
        -------
            True if fingerprint matches, False otherwise.

        """
        session_data = await self.get_session(session_id)
        if not session_data:
            return False

        return self._verify_device_fingerprint(session_data, device_info)


__all__ = ["AuthService"]
