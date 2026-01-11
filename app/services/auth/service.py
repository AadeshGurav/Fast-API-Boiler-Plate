"""Main authentication service combining all auth mixins."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.interfaces.auth_service_interface import AuthServiceInterface
from app.models.auth import LoginResponse
from app.models.user import UserPublic
from app.services.auth.core import AuthCoreMixin
from app.services.auth.session_management import SessionManagementMixin
from app.services.auth.user_management import UserManagementMixin
from app.services.base_service import BaseService

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.core.interfaces.password_service_interface import PasswordServiceInterface
    from app.core.interfaces.rbac_service_interface import RBACServiceInterface
    from app.models.auth import TokenPair
    from app.models.session import DeviceInfo
    from app.models.user import UserCreate
    from app.services.data import DataService
    from app.services.logger import Logger
    from config import Config


class AuthService(
    AuthServiceInterface,
    BaseService,
    AuthCoreMixin,
    UserManagementMixin,
    SessionManagementMixin,
):
    """Main authentication service combining all auth functionality."""

    def __init__(
        self: AuthService,
        logger: Logger,
        config: Config,
        data_service: DataService = None,
        password_service: PasswordServiceInterface = None,
        rbac_service: RBACServiceInterface = None,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize authentication service.

        Args:
        ----
            logger: The logger to use.
            config: The configuration to use.
            data_service: Data service instance.
            password_service: Password service interface.
            rbac_service: RBAC service interface.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        """
        super().__init__(config, logger, *args, **kwargs)

        # Initialize all mixins
        AuthCoreMixin.__init__(
            self,
            logger,
            config,
            data_service,
            password_service,
            rbac_service,
        )
        UserManagementMixin.__init__(self, logger, config, data_service, password_service)
        SessionManagementMixin.__init__(self, logger, data_service)

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

        access_token = super().create_access_token(
            user_id, username, roles, permissions
        )
        refresh_token = super().create_refresh_token(user_id)

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

        return super().create_access_token(user_id, username, roles, permissions)

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
        return super().create_refresh_token(user_id)

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
            # Track failed login attempt (user not found)
            # Note: We can't track this in user object since user doesn't exist
            raise ValueError("Invalid credentials")

        # Track login attempt before password verification
        login_reason = None

        # Verify password - handle both password and password_hash fields
        password_hash = getattr(user, "password_hash", None) or getattr(
            user, "password", None
        )
        if not password_hash:
            self.logger.warning(
                "User has no password hash",
                extra={
                    "service": "AuthService",
                    "username": username,
                    "user_id": user.id,
                },
            )
            login_reason = "User has no password hash"
            # Track failed login attempt
            if hasattr(self, "_add_login_attempt"):
                try:
                    await self._add_login_attempt(
                        user_id=user.id,
                        success=False,
                        device_info=device_info.dict(),
                        reason=login_reason,
                    )
                except Exception as e:  # noqa: BLE001
                    self.logger.warning(
                        "Failed to track login attempt",
                        extra={
                            "service": "AuthService",
                            "user_id": user.id,
                            "error": str(e),
                        },
                    )
            raise ValueError("Invalid credentials")

        if not self.password_service.verify_password(password, password_hash):
            self.logger.warning(
                "Login attempt with invalid password",
                extra={
                    "service": "AuthService",
                    "username": username,
                    "user_id": user.id,
                },
            )
            login_reason = "Invalid credentials"
            # Track failed login attempt
            if hasattr(self, "_add_login_attempt"):
                try:
                    await self._add_login_attempt(
                        user_id=user.id,
                        success=False,
                        device_info=device_info.dict(),
                        reason=login_reason,
                    )
                except Exception as e:  # noqa: BLE001
                    self.logger.warning(
                        "Failed to track login attempt",
                        extra={
                            "service": "AuthService",
                            "user_id": user.id,
                            "error": str(e),
                        },
                    )
            raise ValueError("Invalid credentials")

        # Password verified successfully - continue with login

        # Resolve user permissions
        permissions = await self.rbac_service.resolve_user_permissions(user.id)

        # Create session
        session_id = await self.create_session(user, device_info)

        # Get roles - handle both role (string) and roles (array) fields
        roles = getattr(user, "roles", None) or [getattr(user, "role", "user")]
        if isinstance(roles, str):
            roles = [roles]

        # Create tokens
        token_pair = self.create_token_pair(user.id, user.username, roles, permissions)

        # Track successful login attempt
        if hasattr(self, "_add_login_attempt"):
            try:
                await self._add_login_attempt(
                    user_id=user.id,
                    success=True,
                    device_info=device_info.dict(),
                    reason=None,
                )
            except Exception as e:  # noqa: BLE001
                self.logger.warning(
                    "Failed to track login attempt",
                    extra={
                        "service": "AuthService",
                        "user_id": user.id,
                        "error": str(e),
                    },
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

        # Convert User to UserPublic - only include fields that UserPublic accepts
        user_dict = user.dict()
        # Remove fields that UserPublic doesn't have
        user_public_dict = {
            "id": user_dict.get("id"),
            "username": user_dict.get("username"),
            "email": user_dict.get("email"),
            "roles": user_dict.get("roles", []),
            "groups": user_dict.get("groups", []),
            "status": user_dict.get("status", "active"),
            "metadata": user_dict.get("metadata", {}),
            "created_at": user_dict.get("created_at"),
            "updated_at": user_dict.get("updated_at"),
        }

        return LoginResponse(
            user=UserPublic(**user_public_dict),
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

        # Get roles - handle both role (string) and roles (array) fields
        roles = getattr(user, "roles", None) or [getattr(user, "role", "user")]
        if isinstance(roles, str):
            roles = [roles]

        # Create new token pair
        new_token_pair = self.create_token_pair(
            user.id, user.username, roles, permissions
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
