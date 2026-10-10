"""User management functionality for authentication."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.models.user import User, UserPublic

if TYPE_CHECKING:
    from app.models.user import UserCreate
    from app.services.data import DataService
    from app.services.logger import Logger
    from app.services.password_service import PasswordService
    from config import Config


class UserManager:
    """Registration and user lookups returning API models."""

    def __init__(
        self,
        logger: Logger,
        config: Config,
        data_service: DataService = None,
        password_service: PasswordService = None,
    ) -> None:
        """Initialize user management mixin.

        Args:
        ----
            logger: The logger to use.
            config: The configuration to use.
            data_service: Data service instance.
            password_service: Password service interface.

        Returns:
        -------
            None

        """
        self.logger = logger
        self.config = config
        self.data_service = data_service
        self.password_service = password_service

    async def register_user(self, user_data: UserCreate) -> UserPublic:
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
        existing_user = await self.data_service.users.get_user_by_username(user_data.username)
        if existing_user:
            self.logger.warning(
                "Registration attempt with existing username",
                extra={
                    "service": "UserManager",
                    "username": user_data.username,
                },
            )
            raise ValueError("Username already exists")

        # Check by email
        existing_user = await self.data_service.users.get_user_by_email(user_data.email)
        if existing_user:
            self.logger.warning(
                "Registration attempt with existing email",
                extra={
                    "service": "UserManager",
                    "email": user_data.email,
                },
            )
            raise ValueError("Email already exists")

        self.password_service.assert_password_strength(user_data.password)

        # Hash password
        password_hash = await self.password_service.ahash_password(user_data.password)

        # Extract profile data from metadata
        metadata = user_data.metadata or {}
        profile = {
            "first_name": metadata.get("first_name", ""),
            "last_name": metadata.get("last_name", ""),
            "email": user_data.email,
            "phone": None,
            "avatar": None,
        }

        roles = list(user_data.roles) or [self.config["default_role"]]

        # Create user data with correct structure
        user_dict = {
            "username": user_data.username,
            "password": password_hash,  # Store as "password" not "password_hash"
            "email": user_data.email,  # top level so the unique email index applies
            "roles": roles,
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
            "failed_login_count": 0,
            "locked_until": None,
        }

        # Create user in database
        user_id = await self.data_service.users.create_user(user_dict)
        if not user_id:
            self.logger.error(
                "Failed to create user",
                extra={
                    "service": "UserManager",
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
                    "service": "UserManager",
                    "user_id": user_id,
                },
            )
            raise ValueError("User creation failed")

        # Normalize user data before creating UserPublic
        normalized_user = self.normalize(created_user)

        self.logger.info(
            "User registered successfully",
            extra={
                "service": "UserManager",
                "user_id": user_id,
                "username": user_data.username,
                "email": user_data.email,
            },
        )

        return UserPublic(**normalized_user)

    async def get_user_by_id(self, user_id: str) -> UserPublic | None:
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
        normalized_data = self.normalize(user_data)
        return UserPublic(**normalized_data)

    @staticmethod
    def normalize(user_data: dict) -> dict:
        """Shape a stored user for the User / UserPublic models.

        Args:
        ----
            user_data: User record from the data layer (already normalized by UsersOps).

        Returns:
        -------
            Dictionary accepted by the User model.

        """
        normalized = user_data.copy()
        profile = normalized.get("profile")
        if isinstance(profile, dict):
            normalized.setdefault("metadata", profile.copy())
        return normalized

    async def get_user_by_username(self, username: str) -> User | None:
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
        normalized_data = self.normalize(user_data)
        return User(**normalized_data)
