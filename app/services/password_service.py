"""Password hashing (Argon2id) and the password policy.

Hashing is deliberately slow (tens of milliseconds of CPU), so the ``async`` methods run it
in a worker thread; calling the synchronous ones from a request handler would stall every
other request on the event loop.
"""

from __future__ import annotations

import asyncio
import secrets
import string
from typing import TYPE_CHECKING

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.services.base_service import BaseService

if TYPE_CHECKING:
    from app.services.logger import Logger
    from config import Config

MAX_PASSWORD_LENGTH = 128  # bounds Argon2 work done on attacker-supplied input


class PasswordService(BaseService):
    """Hash, verify and validate passwords; generate reset tokens."""

    def __init__(self, config: Config, logger: Logger) -> None:
        super().__init__(config, logger)
        self.hasher = PasswordHasher()
        self.min_length: int = config["password_min_length"]
        self.require_uppercase: bool = config["password_require_uppercase"]
        self.require_lowercase: bool = config["password_require_lowercase"]
        self.require_digit: bool = config["password_require_digit"]
        self.require_special: bool = config["password_require_special"]
        self.reset_token_lifetime_seconds: int = config["password_reset_token_lifetime"]

    # ---- hashing -------------------------------------------------------------------
    def hash_password(self, password: str) -> str:
        """Argon2id hash (blocking: prefer :meth:`ahash_password` in request handlers)."""
        return self.hasher.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Whether ``password`` matches the hash (blocking: prefer :meth:`averify_password`)."""
        try:
            return self.hasher.verify(password_hash, password)
        except (VerificationError, InvalidHashError):
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        """Whether the hash uses weaker parameters than the current defaults."""
        return self.hasher.check_needs_rehash(password_hash)

    async def ahash_password(self, password: str) -> str:
        """:meth:`hash_password` off the event loop."""
        return await asyncio.to_thread(self.hash_password, password)

    async def averify_password(self, password: str, password_hash: str) -> bool:
        """:meth:`verify_password` off the event loop."""
        return await asyncio.to_thread(self.verify_password, password, password_hash)

    # ---- policy -----------------------------------------------------------------------
    def password_policy(self) -> str:
        """Human-readable description of the password policy."""
        rules = [f"at least {self.min_length} characters"]
        if self.require_uppercase:
            rules.append("an uppercase letter")
        if self.require_lowercase:
            rules.append("a lowercase letter")
        if self.require_digit:
            rules.append("a digit")
        if self.require_special:
            rules.append("a special character")
        return "Password must contain " + ", ".join(rules) + "."

    def validate_password_strength(self, password: str) -> bool:
        """Whether the password meets the configured policy."""
        return (
            self.min_length <= len(password) <= MAX_PASSWORD_LENGTH
            and (not self.require_uppercase or any(c.isupper() for c in password))
            and (not self.require_lowercase or any(c.islower() for c in password))
            and (not self.require_digit or any(c.isdigit() for c in password))
            and (not self.require_special or any(c in string.punctuation for c in password))
        )

    def assert_password_strength(self, password: str) -> None:
        """Raise ``ValueError`` (naming the policy) unless the password is acceptable."""
        if len(password) > MAX_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at most {MAX_PASSWORD_LENGTH} characters.")
        if not self.validate_password_strength(password):
            raise ValueError(self.password_policy())

    @staticmethod
    def generate_reset_token() -> str:
        """An unguessable single-use token (store only its hash)."""
        return secrets.token_urlsafe(32)


__all__ = ["MAX_PASSWORD_LENGTH", "PasswordService"]
