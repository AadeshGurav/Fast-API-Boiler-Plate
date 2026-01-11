"""Password service interface for platform-agnostic password operations."""

from __future__ import annotations

from abc import abstractmethod

from app.core.interfaces.base_interface import BaseInterface


class PasswordServiceInterface(BaseInterface):
    """Interface for password service operations."""

    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Hash a password.

        Args:
        ----
            password: Plain text password

        Returns:
        -------
            Hashed password

        """
        pass

    @abstractmethod
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash.

        Args:
        ----
            password: Plain text password
            password_hash: Hashed password

        Returns:
        -------
            True if password matches

        """
        pass

    @abstractmethod
    def validate_password_strength(self, password: str) -> bool:
        """Validate password strength.

        Args:
        ----
            password: Plain text password

        Returns:
        -------
            True if password meets strength requirements

        """
        pass

    @abstractmethod
    def generate_reset_token(self, user_id: str) -> str:
        """Generate password reset token.

        Args:
        ----
            user_id: User identifier

        Returns:
        -------
            Reset token

        """
        pass

    @abstractmethod
    def verify_reset_token(self, token: str) -> str | None:
        """Verify password reset token.

        Args:
        ----
            token: Reset token

        Returns:
        -------
            User ID if token is valid, None otherwise

        """
        pass


__all__ = ["PasswordServiceInterface"]
