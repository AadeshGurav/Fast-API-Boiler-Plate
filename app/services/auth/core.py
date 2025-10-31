"""Core authentication functionality."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import jwt

from app.models.auth import TokenPair, TokenPayload

if TYPE_CHECKING:
    from app.core.interfaces.password_service_interface import PasswordServiceInterface
    from app.core.interfaces.rbac_service_interface import RBACServiceInterface
    from app.core.interfaces.session_repository_interface import (
        SessionRepositoryInterface,
    )
    from app.core.interfaces.user_repository_interface import UserRepositoryInterface
    from app.services.logger import Logger
    from config import Config


class AuthCoreMixin:
    """Core authentication functionality mixin."""

    def __init__(
        self: AuthCoreMixin,
        logger: Logger,
        config: Config,
        session_repository: SessionRepositoryInterface | None = None,
        user_repository: UserRepositoryInterface | None = None,
        password_service: PasswordServiceInterface | None = None,
        rbac_service: RBACServiceInterface | None = None,
    ) -> None:
        """Initialize auth core mixin.

        Args:
        ----
            logger: The logger to use.
            config: The configuration to use.
            session_repository: Session repository interface.
            user_repository: User repository interface.
            password_service: Password service interface.
            rbac_service: RBAC service interface.

        Returns:
        -------
            None

        """
        self.logger = logger
        self.config = config
        self.session_repository = session_repository
        self.user_repository = user_repository
        self.password_service = password_service
        self.rbac_service = rbac_service

        # JWT configuration
        self.jwt_secret = config.get("jwt_secret", "your-secret-key")
        self.jwt_algorithm = config.get("jwt_algo", "HS256")
        self.access_token_expiry = config.get("jwt_access_token_expiry", 15)  # minutes
        self.refresh_token_expiry = config.get(
            "jwt_refresh_token_expiry", 10080
        )  # minutes

    def create_access_token(
        self: AuthCoreMixin,
        user_id: str,
        username: str,
        roles: list[str],
        permissions: list[str],
    ) -> str:
        """Create JWT access token.

        Args:
        ----
            user_id: User ID.
            username: Username.
            roles: User roles.
            permissions: User permissions.

        Returns:
        -------
            JWT access token.

        """
        payload = TokenPayload(
            user_id=user_id,
            username=username,
            roles=roles,
            permissions=permissions,
            exp=datetime.now(timezone.utc)
            + timedelta(minutes=self.access_token_expiry),
            iat=datetime.now(timezone.utc),
            type="access",
        )

        token = jwt.encode(
            payload.dict(), self.jwt_secret, algorithm=self.jwt_algorithm
        )

        self.logger.debug(
            "Access token created",
            extra={
                "service": "AuthCoreMixin",
                "user_id": user_id,
                "username": username,
                "roles": roles,
                "expires_in": self.access_token_expiry,
            },
        )

        return token

    def create_refresh_token(self: AuthCoreMixin, user_id: str) -> str:
        """Create JWT refresh token.

        Args:
        ----
            user_id: User ID.

        Returns:
        -------
            JWT refresh token.

        """
        payload = TokenPayload(
            user_id=user_id,
            username="",
            roles=[],
            permissions=[],
            exp=datetime.now(timezone.utc)
            + timedelta(minutes=self.refresh_token_expiry),
            iat=datetime.now(timezone.utc),
            type="refresh",
        )

        token = jwt.encode(
            payload.dict(), self.jwt_secret, algorithm=self.jwt_algorithm
        )

        self.logger.debug(
            "Refresh token created",
            extra={
                "service": "AuthCoreMixin",
                "user_id": user_id,
                "expires_in": self.refresh_token_expiry,
            },
        )

        return token

    def verify_token(
        self: AuthCoreMixin, token: str, token_type: str = "access"
    ) -> TokenPayload | None:
        """Verify JWT token.

        Args:
        ----
            token: JWT token to verify.
            token_type: Type of token (access/refresh).

        Returns:
        -------
            TokenPayload if valid, None otherwise.

        """
        try:
            payload = jwt.decode(
                token, self.jwt_secret, algorithms=[self.jwt_algorithm]
            )

            token_payload = TokenPayload(**payload)

            # Check token type
            if token_payload.type != token_type:
                self.logger.warning(
                    "Invalid token type",
                    extra={
                        "service": "AuthCoreMixin",
                        "expected_type": token_type,
                        "actual_type": token_payload.type,
                    },
                )
                return None

            # Check expiration
            if token_payload.exp < datetime.now(timezone.utc):
                self.logger.warning(
                    "Token expired",
                    extra={
                        "service": "AuthCoreMixin",
                        "user_id": token_payload.user_id,
                        "exp": token_payload.exp,
                    },
                )
                return None

            return token_payload

        except jwt.ExpiredSignatureError:
            self.logger.warning(
                "Token signature expired",
                extra={"service": "AuthCoreMixin"},
            )
            return None
        except jwt.InvalidTokenError as e:
            self.logger.warning(
                "Invalid token",
                extra={"service": "AuthCoreMixin", "error": str(e)},
            )
            return None

    def create_token_pair(
        self: AuthCoreMixin,
        user_id: str,
        username: str,
        roles: list[str],
        permissions: list[str],
    ) -> TokenPair:
        """Create access and refresh token pair.

        Args:
        ----
            user_id: User ID.
            username: Username.
            roles: User roles.
            permissions: User permissions.

        Returns:
        -------
            TokenPair with access and refresh tokens.

        """
        access_token = self.create_access_token(user_id, username, roles, permissions)
        refresh_token = self.create_refresh_token(user_id)

        token_pair = TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=self.access_token_expiry * 60,  # Convert to seconds
        )

        self.logger.info(
            "Token pair created",
            extra={
                "service": "AuthCoreMixin",
                "user_id": user_id,
                "username": username,
                "expires_in": token_pair.expires_in,
            },
        )

        return token_pair
