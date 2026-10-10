"""Core authentication functionality: JWT creation and verification."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import jwt
from pydantic import ValidationError

from app.models.auth import TokenPair, TokenPayload

if TYPE_CHECKING:
    from app.services.logger import Logger
    from config import Config

# Symmetric algorithms only: the key is a shared secret, so an asymmetric or "none"
# algorithm from config would either break or disable signature checking.
ALLOWED_JWT_ALGORITHMS = frozenset({"HS256", "HS384", "HS512"})
MIN_JWT_SECRET_LENGTH = 32


class TokenManager:
    """Creates and verifies the JWT access/refresh tokens."""

    def __init__(self, logger: Logger, config: Config) -> None:
        self.logger = logger
        self.config = config

        # JWT configuration. There is deliberately no default secret: a well-known
        # fallback would let anyone mint valid tokens.
        self.jwt_secret = config["jwt_secret"]
        if not self.jwt_secret or len(self.jwt_secret) < MIN_JWT_SECRET_LENGTH:
            raise ValueError(
                f"'jwt_secret' must be set to at least {MIN_JWT_SECRET_LENGTH} "
                "characters. Start via main.py (it generates one into "
                "config.secrets.toml) or set jwt_secret / FABP_JWT_SECRET."
            )
        self.jwt_algorithm = config["jwt_algorithm"]
        if self.jwt_algorithm not in ALLOWED_JWT_ALGORITHMS:
            raise ValueError(
                f"Unsupported jwt_algorithm {self.jwt_algorithm!r}; "
                f"use one of {sorted(ALLOWED_JWT_ALGORITHMS)}."
            )
        self.access_token_expiry = config["access_token_minutes"]
        self.refresh_token_expiry = config["refresh_token_days"] * 24 * 60  # minutes
        self.remember_me_expiry = config["remember_me_days"] * 24 * 60  # minutes

    def _encode(self, payload: TokenPayload) -> str:
        """Sign a payload; exp/iat become numeric claims automatically."""
        return jwt.encode(
            payload.model_dump(mode="python", exclude_none=True),
            self.jwt_secret,
            algorithm=self.jwt_algorithm,
        )

    def create_access_token(
        self,
        user_id: str,
        username: str,
        roles: list[str],
        permissions: list[str],
        sid: str | None = None,
    ) -> str:
        """Create JWT access token.

        Args:
        ----
            user_id: User ID.
            username: Username.
            roles: User roles.
            permissions: User permissions.
            sid: Session the token belongs to.

        Returns:
        -------
            JWT access token.

        """
        now = datetime.now(UTC)
        token = self._encode(
            TokenPayload(
                user_id=user_id,
                username=username,
                roles=roles,
                permissions=permissions,
                exp=now + timedelta(minutes=self.access_token_expiry),
                iat=now,
                type="access",
                sid=sid,
            )
        )

        self.logger.debug(
            "Access token created",
            extra={
                "service": "TokenManager",
                "user_id": user_id,
                "username": username,
                "session_id": sid,
                "expires_in": self.access_token_expiry,
            },
        )
        return token

    def create_refresh_token(
        self,
        user_id: str,
        remember_me: bool = False,
        sid: str | None = None,
    ) -> str:
        """Create JWT refresh token.

        Args:
        ----
            user_id: User ID.
            remember_me: If True, extend refresh token expiry to 30 days.
            sid: Session the token belongs to.

        Returns:
        -------
            JWT refresh token.

        """
        expiry_minutes = self.remember_me_expiry if remember_me else self.refresh_token_expiry
        now = datetime.now(UTC)
        token = self._encode(
            TokenPayload(
                user_id=user_id,
                username="",
                roles=[],
                permissions=[],
                exp=now + timedelta(minutes=expiry_minutes),
                iat=now,
                type="refresh",
                sid=sid,
                remember_me=remember_me,
            )
        )

        self.logger.debug(
            "Refresh token created",
            extra={
                "service": "TokenManager",
                "user_id": user_id,
                "session_id": sid,
                "expires_in": expiry_minutes,
            },
        )
        return token

    def verify_token(
        self,
        token: str,
        token_type: str = "access",  # noqa: S107 - JWT type tag
    ) -> TokenPayload | None:
        """Verify a JWT's signature, expiry and type.

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
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                options={"require": ["exp", "iat"]},
            )
            token_payload = TokenPayload(**payload)
        except jwt.ExpiredSignatureError:
            self.logger.debug("Token expired", extra={"service": "TokenManager"})
            return None
        except (jwt.InvalidTokenError, ValidationError) as e:
            self.logger.warning(
                "Invalid token",
                extra={"service": "TokenManager", "error": str(e)},
            )
            return None

        if token_payload.type != token_type:
            self.logger.warning(
                "Invalid token type",
                extra={
                    "service": "TokenManager",
                    "expected_type": token_type,
                    "actual_type": token_payload.type,
                },
            )
            return None

        return token_payload

    def create_token_pair(
        self,
        user_id: str,
        username: str,
        roles: list[str],
        permissions: list[str],
        remember_me: bool = False,
        sid: str | None = None,
    ) -> TokenPair:
        """Create access and refresh token pair bound to one session.

        Args:
        ----
            user_id: User ID.
            username: Username.
            roles: User roles.
            permissions: User permissions.
            remember_me: If True, extend refresh token expiry to 30 days.
            sid: Session both tokens belong to.

        Returns:
        -------
            TokenPair with access and refresh tokens.

        """
        token_pair = TokenPair(
            access_token=self.create_access_token(user_id, username, roles, permissions, sid),
            refresh_token=self.create_refresh_token(user_id, remember_me, sid),
            token_type="Bearer",  # noqa: S106 - OAuth token type, not a credential
            expires_in=self.access_token_expiry * 60,  # Convert to seconds
        )

        self.logger.info(
            "Token pair created",
            extra={
                "service": "TokenManager",
                "user_id": user_id,
                "username": username,
                "session_id": sid,
                "expires_in": token_pair.expires_in,
            },
        )
        return token_pair
