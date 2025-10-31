"""User management functionality for authentication."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.models.user import User, UserPublic

if TYPE_CHECKING:
    from app.core.interfaces.password_service_interface import PasswordServiceInterface
    from app.core.interfaces.user_repository_interface import UserRepositoryInterface
    from app.models.user import UserCreate
    from app.services.logger import Logger


class UserManagementMixin:
    """User management functionality mixin."""

    def __init__(
        self: UserManagementMixin,
        logger: Logger,
        user_repository: UserRepositoryInterface = None,
        password_service: PasswordServiceInterface = None,
    ) -> None:
        """Initialize user management mixin.

        Args:
        ----
            logger: The logger to use.
            user_repository: User repository interface.
            password_service: Password service interface.

        Returns:
        -------
            None

        """
        self.logger = logger
        self.user_repository = user_repository
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
        if not self.user_repository or not self.password_service:
            raise ValueError("User repository and password service required")

        # Check if user already exists
        existing_user = await self.user_repository.get_user_by_username(
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

        existing_user = await self.user_repository.get_user_by_email(user_data.email)
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

        # Create user data
        user_dict = {
            "username": user_data.username,
            "email": user_data.email,
            "password_hash": password_hash,
            "roles": user_data.roles or ["user"],
            "groups": user_data.groups or [],
            "status": "active",
            "metadata": {},
        }

        # Create user in database
        user_id = await self.user_repository.create_user(user_dict)
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
        created_user = await self.user_repository.get_user_by_id(user_id)
        if not created_user:
            self.logger.error(
                "User created but not found",
                extra={
                    "service": "UserManagementMixin",
                    "user_id": user_id,
                },
            )
            raise ValueError("User creation failed")

        self.logger.info(
            "User registered successfully",
            extra={
                "service": "UserManagementMixin",
                "user_id": user_id,
                "username": user_data.username,
                "email": user_data.email,
            },
        )

        return UserPublic(**created_user)

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
        if not self.user_repository:
            return None

        user_data = await self.user_repository.get_user_by_id(user_id)
        if not user_data:
            return None

        return UserPublic(**user_data)

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
        if not self.user_repository:
            return None

        user_data = await self.user_repository.get_user_by_username(username)
        if not user_data:
            return None

        return User(**user_data)

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
        if not self.user_repository:
            return False

        success = await self.user_repository.update_user(user_id, updates)

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
        if not self.user_repository:
            return False

        success = await self.user_repository.assign_roles(user_id, roles)

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
        if not self.user_repository:
            return False

        success = await self.user_repository.assign_groups(user_id, groups)

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
