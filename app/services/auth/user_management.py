"""User management functionality for authentication."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.models.user import User, UserPublic

if TYPE_CHECKING:
    from app.core.interfaces.password_service_interface import PasswordServiceInterface
    from app.models.user import UserCreate
    from app.services.data import DataService
    from app.services.logger import Logger


class UserManagementMixin:
    """User management functionality mixin."""

    def __init__(
        self: UserManagementMixin,
        logger: Logger,
        data_service: DataService = None,
        password_service: PasswordServiceInterface = None,
    ) -> None:
        """Initialize user management mixin.

        Args:
        ----
            logger: The logger to use.
            data_service: Data service instance.
            password_service: Password service interface.

        Returns:
        -------
            None

        """
        self.logger = logger
        self.data_service = data_service
        self.password_service = password_service

    async def register_user(
        self: UserManagementMixin, user_data: UserCreate
    ) -> UserPublic:
        """Register a new user.

        Args:
        ----
            user_data: User creation data.

        Returns:
        -------
            Created user (public data).

        """
        if not self.data_service or not self.password_service:
            raise ValueError("Data service and password service required")

        # Check if user already exists
        existing_user = await self.data_service.users.get_user_by_username(
            user_data.username
        )
        if existing_user:
            self.logger.warning(
                "Registration attempt with existing username",
                extra={
                    "service": "UserManagementMixin",
                    "username": user_data.username,
                },
            )
            raise ValueError("Username already exists")

        # Check by email - check both top-level email and profile.email
        existing_user = await self.data_service.users.get_user_by_email(user_data.email)
        if not existing_user:
            # Also check in profile.email using data service
            existing_user = await self.data_service.get(
                "users", {"profile.email": user_data.email}, policy=None
            )
        if existing_user:
            self.logger.warning(
                "Registration attempt with existing email",
                extra={
                    "service": "UserManagementMixin",
                    "email": user_data.email,
                },
            )
            raise ValueError("Email already exists")

        # Hash password
        password_hash = self.password_service.hash_password(user_data.password)

        # Extract profile data from metadata
        metadata = user_data.metadata or {}
        profile = {
            "first_name": metadata.get("first_name", ""),
            "last_name": metadata.get("last_name", ""),
            "email": user_data.email,
            "phone": None,
            "avatar": None,
        }

        # Determine role from roles array or default to "user"
        role = user_data.roles[0] if user_data.roles else "user"

        # Create user data with correct structure
        user_dict = {
            "username": user_data.username,
            "password": password_hash,  # Store as "password" not "password_hash"
            "role": role,  # Store as "role" (string) not "roles" (array)
            "groups": user_data.groups or [],
            "permissions": [],  # Will be resolved by RBAC
            "tokens": [],
            "theme": "light",
            "profile": profile,
            "preferences": {
                "language": "en",
                "timezone": "UTC",
                "notifications": {
                    "email": metadata.get("newsletter", False),
                    "push": False,
                    "sms": False,
                },
            },
            "status": "active",
            "last_login": None,
            "login_attempts": 0,  # Counter for backward compatibility
            "login_attempts_history": [],  # Array of login attempt history
            "sessions": [],  # Array of session references
            "locked_until": None,
        }

        # Create user in database
        user_id = await self.data_service.users.create_user(user_dict)
        if not user_id:
            self.logger.error(
                "Failed to create user",
                extra={
                    "service": "UserManagementMixin",
                    "username": user_data.username,
                },
            )
            raise ValueError("Failed to create user")

        # Get created user
        created_user = await self.data_service.users.get_user_by_id(user_id)
        if not created_user:
            self.logger.error(
                "User created but not found",
                extra={
                    "service": "UserManagementMixin",
                    "user_id": user_id,
                },
            )
            raise ValueError("User creation failed")

        # Normalize user data before creating UserPublic
        normalized_user = self._normalize_user_data(created_user)

        self.logger.info(
            "User registered successfully",
            extra={
                "service": "UserManagementMixin",
                "user_id": user_id,
                "username": user_data.username,
                "email": user_data.email,
            },
        )

        return UserPublic(**normalized_user)

    async def get_user_by_id(
        self: UserManagementMixin, user_id: str
    ) -> UserPublic | None:
        """Get user by ID.

        Args:
        ----
            user_id: User ID.

        Returns:
        -------
            User public data if found, None otherwise.

        """
        if not self.data_service:
            return None

        user_data = await self.data_service.users.get_user_by_id(user_id)
        if not user_data:
            return None

        # Normalize user data for UserPublic model
        normalized_data = self._normalize_user_data(user_data)
        return UserPublic(**normalized_data)

    def _normalize_user_data(self: UserManagementMixin, user_data: dict) -> dict:
        """Normalize user data from database to User model format.

        Args:
        ----
            user_data: User data from database.

        Returns:
        -------
            Normalized user data compatible with User model.

        """
        normalized = user_data.copy()

        # Convert password to password_hash for User model
        if "password" in normalized and "password_hash" not in normalized:
            normalized["password_hash"] = normalized.pop("password")

        # Convert role to roles array for User model
        if "role" in normalized and "roles" not in normalized:
            normalized["roles"] = [normalized.pop("role")]

        # Extract email from profile if not at top level
        if "profile" in normalized and isinstance(normalized["profile"], dict):
            profile = normalized["profile"]
            if "email" not in normalized and "email" in profile:
                normalized["email"] = profile["email"]

        # Convert profile to metadata for User model
        if "profile" in normalized and "metadata" not in normalized:
            normalized["metadata"] = normalized.get("profile", {}).copy()

        # Ensure sessions and login_attempts arrays exist (backward compatibility)
        if "sessions" not in normalized:
            normalized["sessions"] = []

        # Handle login_attempts - convert from int to list if needed
        # First, check if login_attempts_history exists (new format)
        if "login_attempts_history" in normalized:
            # New format: use login_attempts_history
            normalized["login_attempts"] = normalized.pop("login_attempts_history")
        # Then check if login_attempts exists and handle it
        elif "login_attempts" in normalized:
            # Check if it's an integer (old format) or already a list
            if isinstance(normalized["login_attempts"], int):
                # Old format: convert integer counter to empty list
                # Remove the integer field and set to empty list
                normalized.pop("login_attempts")
                normalized["login_attempts"] = []
            elif not isinstance(normalized["login_attempts"], list):
                # Not a list and not an int - default to empty list
                normalized["login_attempts"] = []
        else:
            # Neither exists - default to empty list
            normalized["login_attempts"] = []

        return normalized

    def _limit_sessions_array(
        self: UserManagementMixin, sessions: list[dict]
    ) -> list[dict]:
        """Limit sessions array to last 10 sessions.

        Args:
        ----
            sessions: List of session references.

        Returns:
        -------
            Limited list of sessions (max 10).

        """
        if not sessions:
            return []

        def _get_timestamp(session: dict) -> datetime:
            """Extract and normalize timestamp from session."""
            created_at = session.get("created_at")
            if created_at is None:
                return datetime.min.replace(tzinfo=timezone.utc)
            if isinstance(created_at, str):
                try:
                    created_at = created_at.replace("Z", "+00:00")
                    return datetime.fromisoformat(created_at)
                except (ValueError, AttributeError):
                    return datetime.min.replace(tzinfo=timezone.utc)
            if isinstance(created_at, datetime):
                # Ensure timezone-aware
                if created_at.tzinfo is None:
                    return created_at.replace(tzinfo=timezone.utc)
                return created_at
            return datetime.min.replace(tzinfo=timezone.utc)

        # Sort by created_at descending and take last 10
        sorted_sessions = sorted(
            sessions,
            key=_get_timestamp,
            reverse=True,
        )
        return sorted_sessions[:10]

    def _limit_attempts_array(
        self: UserManagementMixin, attempts: list[dict]
    ) -> list[dict]:
        """Limit login_attempts array to last 50 attempts.

        Args:
        ----
            attempts: List of login attempts.

        Returns:
        -------
            Limited list of attempts (max 50).

        """
        if not attempts:
            return []

        def _get_timestamp(attempt: dict) -> datetime:
            """Extract and normalize timestamp from attempt."""
            timestamp = attempt.get("timestamp")
            if timestamp is None:
                return datetime.min.replace(tzinfo=timezone.utc)
            if isinstance(timestamp, str):
                try:
                    timestamp = timestamp.replace("Z", "+00:00")
                    return datetime.fromisoformat(timestamp)
                except (ValueError, AttributeError):
                    return datetime.min.replace(tzinfo=timezone.utc)
            if isinstance(timestamp, datetime):
                # Ensure timezone-aware
                if timestamp.tzinfo is None:
                    return timestamp.replace(tzinfo=timezone.utc)
                return timestamp
            return datetime.min.replace(tzinfo=timezone.utc)

        # Sort by timestamp descending and take last 50
        sorted_attempts = sorted(
            attempts,
            key=_get_timestamp,
            reverse=True,
        )
        return sorted_attempts[:50]

    async def _add_session_to_user(
        self: UserManagementMixin,
        user_id: str,
        session_id: str,
        device_info: dict,
        created_at: datetime,
        expires_at: datetime | float,
    ) -> bool:
        """Add session reference to user's sessions array.

        Args:
        ----
            user_id: User ID.
            session_id: Session ID.
            device_info: Device information dictionary.
            created_at: Session creation timestamp.
            expires_at: Session expiration timestamp.

        Returns:
        -------
            True if successful, False otherwise.

        """
        if not self.data_service:
            return False

        # Get current user data
        user_data = await self.data_service.users.get_user_by_id(user_id)
        if not user_data:
            return False

        # Get current sessions array
        sessions = user_data.get("sessions", [])
        if not isinstance(sessions, list):
            sessions = []

        # Convert expires_at to datetime if it's a timestamp
        if isinstance(expires_at, (int, float)):
            expires_at = datetime.fromtimestamp(expires_at, tz=timezone.utc)

        # Ensure created_at is timezone-aware
        if isinstance(created_at, datetime):
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
        elif isinstance(created_at, str):
            try:
                created_at = created_at.replace("Z", "+00:00")
                created_at = datetime.fromisoformat(created_at)
            except (ValueError, AttributeError):
                created_at = datetime.now(timezone.utc)

        # Create session reference
        session_ref = {
            "id": session_id,
            "device_info": device_info,
            "created_at": created_at,
            "expires_at": expires_at,
            "revoked_at": None,
            "is_active": True,
        }

        # Add new session to the beginning
        sessions.insert(0, session_ref)

        # Limit to last 10 sessions
        sessions = self._limit_sessions_array(sessions)

        # Update user
        return await self.data_service.users.update_user(
            user_id, {"sessions": sessions}
        )

    async def _add_login_attempt(
        self: UserManagementMixin,
        user_id: str,
        success: bool,
        device_info: dict,
        reason: str | None = None,
    ) -> bool:
        """Add login attempt to user's login_attempts array.

        Args:
        ----
            user_id: User ID.
            success: Whether login was successful.
            device_info: Device information dictionary.
            reason: Failure reason if unsuccessful.

        Returns:
        -------
            True if successful, False otherwise.

        """
        if not self.data_service:
            return False

        # Get current user data
        user_data = await self.data_service.users.get_user_by_id(user_id)
        if not user_data:
            return False

        # Get current login_attempts array
        attempts = user_data.get(
            "login_attempts_history", user_data.get("login_attempts", [])
        )
        if not isinstance(attempts, list):
            attempts = []

        # Create attempt record
        attempt = {
            "timestamp": datetime.now(timezone.utc),
            "success": success,
            "ip_address": device_info.get("ip_address", ""),
            "user_agent": device_info.get("user_agent", ""),
            "device_info": device_info,
            "reason": reason,
        }

        # Add new attempt to the beginning
        attempts.insert(0, attempt)

        # Limit to last 50 attempts
        attempts = self._limit_attempts_array(attempts)

        # Update user (use login_attempts_history for new format, login_attempts for backward compatibility)
        updates = {"login_attempts_history": attempts}
        # Also update counter for backward compatibility
        if "login_attempts" in user_data and isinstance(
            user_data["login_attempts"], int
        ):
            updates["login_attempts"] = user_data["login_attempts"] + (
                0 if success else 1
            )

        return await self.data_service.users.update_user(user_id, updates)

    async def _update_user_session(
        self: UserManagementMixin,
        user_id: str,
        session_id: str,
        revoked: bool = False,
    ) -> bool:
        """Update session reference in user's sessions array.

        Args:
        ----
            user_id: User ID.
            session_id: Session ID.
            revoked: Whether session is revoked.

        Returns:
        -------
            True if successful, False otherwise.

        """
        if not self.data_service:
            return False

        # Get current user data
        user_data = await self.data_service.users.get_user_by_id(user_id)
        if not user_data:
            return False

        # Get current sessions array
        sessions = user_data.get("sessions", [])
        if not isinstance(sessions, list):
            sessions = []

        # Find and update session
        updated = False
        for session in sessions:
            if session.get("id") == session_id:
                if revoked:
                    session["revoked_at"] = datetime.now(timezone.utc)
                    session["is_active"] = False
                updated = True
                break

        if updated:
            # Update user
            return await self.data_service.users.update_user(
                user_id, {"sessions": sessions}
            )

        return False

    async def _update_user_sessions(
        self: UserManagementMixin,
        user_id: str,
        except_session_id: str | None = None,
    ) -> bool:
        """Update all session references in user's sessions array.

        Args:
        ----
            user_id: User ID.
            except_session_id: Session ID to exclude from update.

        Returns:
        -------
            True if successful, False otherwise.

        """
        if not self.data_service:
            return False

        # Get current user data
        user_data = await self.data_service.users.get_user_by_id(user_id)
        if not user_data:
            return False

        # Get current sessions array
        sessions = user_data.get("sessions", [])
        if not isinstance(sessions, list):
            sessions = []

        # Update all sessions except the excluded one
        updated = False
        now = datetime.now(timezone.utc)
        for session in sessions:
            if except_session_id and session.get("id") == except_session_id:
                continue
            if session.get("is_active", True):
                session["revoked_at"] = now
                session["is_active"] = False
                updated = True

        if updated:
            # Update user
            return await self.data_service.users.update_user(
                user_id, {"sessions": sessions}
            )

        return False

    async def get_user_by_username(
        self: UserManagementMixin, username: str
    ) -> User | None:
        """Get user by username.

        Args:
        ----
            username: Username.

        Returns:
        -------
            User if found, None otherwise.

        """
        if not self.data_service:
            return None

        user_data = await self.data_service.users.get_user_by_username(username)
        if not user_data:
            return None

        # Normalize user data for User model
        normalized_data = self._normalize_user_data(user_data)
        return User(**normalized_data)

    async def update_user(
        self: UserManagementMixin, user_id: str, updates: dict
    ) -> bool:
        """Update user data.

        Args:
        ----
            user_id: User ID.
            updates: Updates to apply.

        Returns:
        -------
            True if updated successfully, False otherwise.

        """
        if not self.data_service:
            return False

        success = await self.data_service.users.update_user(user_id, updates)

        if success:
            self.logger.info(
                "User updated",
                extra={
                    "service": "UserManagementMixin",
                    "user_id": user_id,
                    "updates": list(updates.keys()),
                },
            )
        else:
            self.logger.warning(
                "Failed to update user",
                extra={
                    "service": "UserManagementMixin",
                    "user_id": user_id,
                },
            )

        return success

    async def assign_roles(
        self: UserManagementMixin, user_id: str, roles: list[str]
    ) -> bool:
        """Assign roles to user.

        Args:
        ----
            user_id: User ID.
            roles: List of role IDs.

        Returns:
        -------
            True if assigned successfully, False otherwise.

        """
        if not self.data_service:
            return False

        success = await self.data_service.users.assign_roles(user_id, roles)

        if success:
            self.logger.info(
                "Roles assigned to user",
                extra={
                    "service": "UserManagementMixin",
                    "user_id": user_id,
                    "roles": roles,
                },
            )
        else:
            self.logger.warning(
                "Failed to assign roles",
                extra={
                    "service": "UserManagementMixin",
                    "user_id": user_id,
                    "roles": roles,
                },
            )

        return success

    async def assign_groups(
        self: UserManagementMixin, user_id: str, groups: list[str]
    ) -> bool:
        """Assign groups to user.

        Args:
        ----
            user_id: User ID.
            groups: List of group IDs.

        Returns:
        -------
            True if assigned successfully, False otherwise.

        """
        if not self.data_service:
            return False

        success = await self.data_service.users.assign_groups(user_id, groups)

        if success:
            self.logger.info(
                "Groups assigned to user",
                extra={
                    "service": "UserManagementMixin",
                    "user_id": user_id,
                    "groups": groups,
                },
            )
        else:
            self.logger.warning(
                "Failed to assign groups",
                extra={
                    "service": "UserManagementMixin",
                    "user_id": user_id,
                    "groups": groups,
                },
            )

        return success
