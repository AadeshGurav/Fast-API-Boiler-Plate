"""Main authentication service combining all auth mixins."""

from __future__ import annotations

import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from app.models.auth import LoginResponse, TokenPair
from app.models.user import User, UserPublic
from app.services.auth.mfa import MFAError, MFAService
from app.services.auth.sessions import SessionManager
from app.services.auth.tokens import TokenManager
from app.services.auth.users import UserManager
from app.services.base_service import BaseService
from app.services.data.policies import CachePolicy
from app.services.data.sessions_ops import hash_token, is_session_active
from app.services.mailer import send_password_reset_email

if TYPE_CHECKING:
    from app.models.auth import TokenPayload
    from app.models.session import DeviceInfo
    from app.models.user import UserCreate
    from app.services.audit import AuditService
    from app.services.data import DataService
    from app.services.logger import Logger
    from app.services.password_service import PasswordService
    from app.services.rbac import RBACService
    from config import Config

GENERIC_LOGIN_ERROR = "Invalid credentials"
RESET_REQUESTED_MESSAGE = "If the email exists, a reset link has been sent"


class AuthenticationError(ValueError):
    """Credentials, account state or token were rejected.

    A ``ValueError`` subclass so existing ``except ValueError`` handlers (which map
    to HTTP 401) keep working. The message is safe to show to the caller.
    """


class MFARequiredError(AuthenticationError):
    """The password was right; a second factor is needed. Carries the challenge token."""

    def __init__(self, mfa_token: str) -> None:
        super().__init__("Two-factor authentication code required")
        self.mfa_token = mfa_token


class AuthService(BaseService):
    """Login, token refresh, logout, registration and password reset.

    Composes three collaborators instead of inheriting from them:
    ``tokens`` (JWT), ``sessions`` (server-side session records) and ``users``
    (registration and lookups).
    """

    def __init__(
        self,
        logger: Logger,
        config: Config,
        data_service: DataService,
        password_service: PasswordService,
        rbac_service: RBACService,
        audit: AuditService,
    ) -> None:
        super().__init__(config, logger)
        self.data_service = data_service
        self.password_service = password_service
        self.rbac_service = rbac_service
        self.audit = audit

        self.tokens = TokenManager(logger, config)
        self.sessions = SessionManager(
            logger, data_service, config["refresh_token_days"], config["remember_me_days"]
        )
        self.users = UserManager(logger, config, data_service, password_service)
        self.mfa = MFAService(config, logger, data_service, password_service, audit)

        self.max_failed_logins: int = config["auth_max_failed_logins"]
        self.lockout_minutes: int = config["auth_lockout_minutes"]
        self.refresh_reuse_grace_seconds: int = config["auth_refresh_reuse_grace_seconds"]
        self._timing_hash: str | None = None

    # ------------------------------------------------------------- collaborators
    def verify_token(self, token: str, token_type: str = "access") -> TokenPayload | None:  # noqa: S107
        """Verify a JWT's signature, expiry and type (None if invalid)."""
        return self.tokens.verify_token(token, token_type)

    async def is_session_active(self, session_id: str | None) -> bool:
        """Whether the session exists, is unrevoked and unexpired."""
        return await self.sessions.is_session_active(session_id)

    # ------------------------------------------------------------------- login
    async def register_user(self: AuthService, user_data: UserCreate) -> UserPublic:
        """Register a new user (see ``UserManagementMixin.register_user``)."""
        user = await self.users.register_user(user_data)
        await self.audit.record(
            "user.registered", target_type="user", target_id=user.id, actor_id=user.id
        )
        return user

    async def _record_login_attempt(
        self: AuthService,
        username: str,
        user_id: str | None,
        success: bool,
        device_info: DeviceInfo,
        reason: str | None = None,
    ) -> None:
        """Append to the login audit log. Never lets an audit failure block a login."""
        try:
            await self.data_service.insert(
                "login_attempts",
                {
                    "id": uuid.uuid4().hex,
                    "timestamp": datetime.now(UTC),
                    "username": username[:255],
                    "user_id": user_id,
                    "success": success,
                    "reason": reason,
                    "ip_address": device_info.ip_address,
                    "user_agent": device_info.user_agent,
                },
            )
        except Exception as e:
            self.logger.error(
                "Failed to record login attempt",
                extra={"service": "AuthService", "user_id": user_id, "error": str(e)},
            )

    async def _equalize_timing(self: AuthService, password: str) -> None:
        """Spend the same time hashing for unknown users as for known ones.

        Without this, "no such user" returns in microseconds while a wrong password
        takes a full Argon2 verification, letting attackers enumerate usernames.
        """
        if self._timing_hash is None:
            self._timing_hash = await self.password_service.ahash_password(
                secrets.token_urlsafe(16)
            )
        await self.password_service.averify_password(password, self._timing_hash)

    @staticmethod
    def _locked(user: dict[str, Any]) -> bool:
        locked_until = user.get("locked_until")
        return isinstance(locked_until, datetime) and locked_until > datetime.now(UTC)

    async def authenticate(
        self: AuthService, username: str, password: str, device_info: DeviceInfo
    ) -> User:
        """Check credentials and account state; enforce and record lockout.

        Args:
        ----
            username: Username.
            password: Plain-text password.
            device_info: Where the attempt came from.

        Returns:
        -------
            The authenticated user.

        Raises:
        ------
            AuthenticationError: Always with the same generic message, whatever the cause
                (unknown user, wrong password, disabled or locked account).

        """
        users = self.data_service.users
        record = await users.get_user_by_username(username, fresh=True)

        if record is None:
            await self._equalize_timing(password)
            await self._record_login_attempt(username, None, False, device_info, "unknown_user")
            raise AuthenticationError(GENERIC_LOGIN_ERROR)

        user_id = record["id"]
        if record.get("status", "active") != "active":
            await self._equalize_timing(password)
            await self._record_login_attempt(
                username, user_id, False, device_info, "account_inactive"
            )
            raise AuthenticationError(GENERIC_LOGIN_ERROR)

        if self._locked(record):
            await self._equalize_timing(password)
            await self._record_login_attempt(
                username, user_id, False, device_info, "account_locked"
            )
            raise AuthenticationError(GENERIC_LOGIN_ERROR)

        # Reserve the attempt *before* verifying: the increment is atomic, so of a burst of
        # parallel guesses only ``max_failed_logins`` ever reach the (expensive) verify.
        failures = await users.increment_failed_logins(record)
        if failures > self.max_failed_logins:
            await self._equalize_timing(password)
            await self._record_login_attempt(
                username, user_id, False, device_info, "account_locked"
            )
            raise AuthenticationError(GENERIC_LOGIN_ERROR)

        password_hash = record.get("password_hash")
        if not password_hash or not await self.password_service.averify_password(
            password, password_hash
        ):
            if failures >= self.max_failed_logins:
                await users.update_user(
                    user_id,
                    {
                        "locked_until": datetime.now(UTC) + timedelta(minutes=self.lockout_minutes),
                        "failed_login_count": 0,
                    },
                )
                self.logger.warning(
                    "Account locked after repeated failed logins",
                    extra={"service": "AuthService", "user_id": user_id},
                )
            await self._record_login_attempt(
                username, user_id, False, device_info, "invalid_password"
            )
            raise AuthenticationError(GENERIC_LOGIN_ERROR)

        upgrade = {}
        if self.password_service.needs_rehash(password_hash):  # hashing parameters were raised
            upgrade["password"] = await self.password_service.ahash_password(password)
        await users.update_user(
            user_id,
            {
                "failed_login_count": 0,
                "locked_until": None,
                "last_login": datetime.now(UTC),
                **upgrade,
            },
        )
        await self._record_login_attempt(username, user_id, True, device_info)
        return User(**self.users.normalize(record))

    async def _open_session(
        self: AuthService, user: User, device_info: DeviceInfo, remember_me: bool
    ) -> LoginResponse:
        """Create a session and the token pair bound to it."""
        permissions = await self.rbac_service.resolve_user_permissions(user.id)
        session_id = uuid.uuid4().hex
        token_pair = self.tokens.create_token_pair(
            user.id,
            user.username,
            user.roles,
            permissions,
            remember_me,
            sid=session_id,
        )
        await self.sessions.create_session(
            user,
            device_info,
            remember_me,
            session_id=session_id,
            refresh_token=token_pair.refresh_token,
        )

        self.logger.info(
            "User logged in",
            extra={
                "service": "AuthService",
                "user_id": user.id,
                "username": user.username,
                "session_id": session_id,
            },
        )
        return LoginResponse(
            user=UserPublic(**user.model_dump()),
            tokens=token_pair,
            permissions=permissions,
            session_id=session_id,
        )

    async def login_user(
        self: AuthService,
        username: str,
        password: str,
        device_info: DeviceInfo,
        remember_me: bool = False,
    ) -> LoginResponse:
        """Log in with username and password.

        Args:
        ----
            username: Username.
            password: Password.
            device_info: Device information.
            remember_me: If True, extend session and token expiry to 30 days.

        Returns:
        -------
            Login response with user, tokens, and permissions.

        """
        user = await self.authenticate(username, password, device_info)
        if await self.mfa.is_enabled(user.id):
            raise MFARequiredError(
                self.tokens.create_mfa_token(
                    user.id, remember_me, self.config["mfa_challenge_minutes"]
                )
            )
        return await self._open_session(user, device_info, remember_me)

    async def complete_mfa_login(
        self: AuthService, mfa_token: str, code: str, device_info: DeviceInfo
    ) -> tuple[LoginResponse, bool]:
        """Second step of a two-factor sign-in: exchange the challenge and a code for a session.

        Wrong codes count towards the same lockout as wrong passwords. Returns the login
        response and the "remember me" choice made at the password step.
        """
        claims = self.tokens.verify_mfa_token(mfa_token)
        if claims is None:
            raise AuthenticationError("The sign-in attempt expired; sign in again")
        user_id, remember_me = claims
        users = self.data_service.users
        record = await users.get_user_by_id(user_id, fresh=True)
        if not record or record.get("status", "active") != "active" or self._locked(record):
            raise AuthenticationError(GENERIC_LOGIN_ERROR)

        failures = await users.increment_failed_logins(record)
        if failures > self.max_failed_logins or not await self.mfa.verify(user_id, code):
            if failures >= self.max_failed_logins:
                await users.update_user(
                    user_id,
                    {
                        "locked_until": datetime.now(UTC) + timedelta(minutes=self.lockout_minutes),
                        "failed_login_count": 0,
                    },
                )
            await self._record_login_attempt(
                record["username"], user_id, False, device_info, "invalid_mfa_code"
            )
            raise AuthenticationError("The code is not valid")

        await users.update_user(user_id, {"failed_login_count": 0})
        await self._record_login_attempt(record["username"], user_id, True, device_info, "mfa")
        response = await self._open_session(
            User(**self.users.normalize(record)), device_info, remember_me
        )
        return response, remember_me

    async def login_oauth_user(
        self: AuthService, user: User, device_info: DeviceInfo
    ) -> LoginResponse:
        """Open a session for a user already verified by an OAuth provider."""
        record = await self.data_service.users.get_user_by_id(user.id, fresh=True)
        if record is None or record.get("status", "active") != "active":
            raise AuthenticationError(GENERIC_LOGIN_ERROR)
        return await self._open_session(user, device_info, remember_me=False)

    # ----------------------------------------------------------------- refresh
    async def refresh_tokens(
        self: AuthService, refresh_token: str, device_info: DeviceInfo
    ) -> TokenPair:
        """Rotate the refresh token and issue a new pair for the same session.

        Every refresh token is single-use. Presenting one that was already rotated
        (outside a short grace window for parallel tabs/requests) means it leaked,
        so the whole session is revoked.

        Args:
        ----
            refresh_token: Current refresh token.
            device_info: Device information.

        Returns:
        -------
            New token pair.

        Raises:
        ------
            AuthenticationError: If the token, session or user is no longer valid.

        """
        payload = self.tokens.verify_token(refresh_token, "refresh")
        if not payload or not payload.sid:
            raise AuthenticationError("Invalid refresh token")

        session = await self.sessions.get_session(payload.sid)
        if not is_session_active(session) or session.get("user_id") != payload.user_id:
            raise AuthenticationError("Session expired or revoked")

        presented = hash_token(refresh_token)
        if not self._is_current_refresh_token(session, presented):
            await self.sessions.revoke_session(payload.sid)
            self.logger.warning(
                "Refresh token reuse detected; session revoked",
                extra={
                    "service": "AuthService",
                    "user_id": payload.user_id,
                    "session_id": payload.sid,
                },
            )
            raise AuthenticationError("Session expired or revoked")

        user = await self.users.get_user_by_id(payload.user_id)
        record = await self.data_service.users.get_user_by_id(payload.user_id, fresh=True)
        if not user or not record or record.get("status", "active") != "active":
            await self.sessions.revoke_session(payload.sid)
            raise AuthenticationError("Session expired or revoked")

        permissions = await self.rbac_service.resolve_user_permissions(user.id)
        new_pair = self.tokens.create_token_pair(
            user.id,
            user.username,
            user.roles,
            permissions,
            remember_me=payload.remember_me,
            sid=payload.sid,
        )
        await self.data_service.sessions.update_session(
            payload.sid,
            {
                "refresh_token_hash": hash_token(new_pair.refresh_token),
                "previous_refresh_token_hash": session.get("refresh_token_hash"),
                "rotated_at": datetime.now(UTC),
                "last_used_at": datetime.now(UTC),
            },
        )

        self.logger.info(
            "Tokens refreshed",
            extra={
                "service": "AuthService",
                "user_id": user.id,
                "session_id": payload.sid,
            },
        )
        return new_pair

    def _is_current_refresh_token(
        self: AuthService, session: dict[str, Any], presented_hash: str
    ) -> bool:
        """Whether the presented hash is the session's latest refresh token, or the
        previous one still inside the rotation grace window."""
        if hmac.compare_digest(session.get("refresh_token_hash") or "", presented_hash):
            return True

        previous = session.get("previous_refresh_token_hash")
        rotated_at = session.get("rotated_at")
        if not previous or not isinstance(rotated_at, datetime):
            return False
        within_grace = (
            datetime.now(UTC) - rotated_at
        ).total_seconds() <= self.refresh_reuse_grace_seconds
        return within_grace and hmac.compare_digest(previous, presented_hash)

    # ------------------------------------------------------------------ logout
    async def logout(self: AuthService, session_id: str) -> bool:
        """Log out by revoking the session (and with it every token issued for it)."""
        success = await self.sessions.revoke_session(session_id)
        if success:
            await self.audit.record("session.revoked", target_type="session", target_id=session_id)
            self.logger.info(
                "User logged out",
                extra={"service": "AuthService", "session_id": session_id},
            )
        return success

    async def logout_all_devices(
        self: AuthService, user_id: str, except_session_id: str | None = None
    ) -> int:
        """Revoke all of a user's sessions except one; returns how many."""
        revoked = await self.sessions.revoke_user_sessions(user_id, except_session_id)
        await self.audit.record(
            "session.revoked_all", target_type="user", target_id=user_id, details={"count": revoked}
        )
        return revoked

    async def change_password(
        self, user_id: str, current_password: str, new_password: str, keep_session_id: str | None
    ) -> int:
        """Change a password after re-checking the current one.

        Every other session is ended (a stolen session should not survive a password
        change); the caller's own stays signed in.

        Returns:
        -------
            Number of other sessions ended.

        Raises:
        ------
            AuthenticationError: If the current password is wrong.
            ValueError: If the new password does not meet the policy.

        """
        record = await self.data_service.users.get_user_by_id(user_id, fresh=True)
        if not record or not await self.password_service.averify_password(
            current_password, record.get("password_hash") or ""
        ):
            raise AuthenticationError("Current password is incorrect")
        self.password_service.assert_password_strength(new_password)
        await self.data_service.users.update_user(
            user_id, {"password": await self.password_service.ahash_password(new_password)}
        )
        ended = await self.sessions.revoke_user_sessions(user_id, keep_session_id)
        await self.audit.record(
            "user.password_changed",
            target_type="user",
            target_id=user_id,
            details={"sessions_ended": ended},
        )
        return ended

    async def set_user_status(self, user_id: str, status: str) -> bool:
        """Enable or disable an account; disabling ends all of its sessions."""
        if not await self.data_service.users.update_user(user_id, {"status": status}):
            return False
        if status != "active":
            await self.sessions.revoke_user_sessions(user_id)
        await self.audit.record(
            "user.status_changed", target_type="user", target_id=user_id, details={"status": status}
        )
        return True

    async def delete_user(self, user_id: str) -> bool:
        """Permanently delete an account and end its sessions."""
        await self.sessions.revoke_user_sessions(user_id)
        deleted = await self.data_service.users.delete_user(user_id)
        if deleted:
            await self.audit.record("user.deleted", target_type="user", target_id=user_id)
        return deleted

    # --------------------------------------------------------- password resets
    async def request_password_reset(self: AuthService, email: str) -> dict[str, str]:
        """Generate a single-use reset token and email it.

        The response is identical whether or not the email is registered.
        """
        user = await self.data_service.users.get_user_by_email(email)
        if not user:
            self.logger.warning(
                "Password reset requested for unknown email",
                extra={"service": "AuthService"},
            )
            return {"message": RESET_REQUESTED_MESSAGE}

        token = self.password_service.generate_reset_token()
        token_hash = hash_token(token)
        now = datetime.now(UTC)

        # Only the newest link may work: expire any earlier unused tokens.
        for old in await self.data_service.find_many(
            "password_reset_tokens",
            {"user_id": user["id"], "used_at": None},
            policy=CachePolicy.DB_ONLY,
        ):
            await self.data_service.update(
                "password_reset_tokens",
                {"token_hash": old["token_hash"]},
                {"used_at": now},
                policy=CachePolicy.DB_ONLY,
            )

        await self.data_service.insert(
            "password_reset_tokens",
            {
                "token_hash": token_hash,
                "user_id": user["id"],
                "created_at": now,
                "expires_at": now
                + timedelta(seconds=self.password_service.reset_token_lifetime_seconds),
                "used_at": None,
            },
        )

        await send_password_reset_email(self.config, self.logger, email, token)
        return {"message": RESET_REQUESTED_MESSAGE}

    async def confirm_password_reset(self: AuthService, token: str, new_password: str) -> bool:
        """Set a new password using a reset token, then end every session.

        Raises:
        ------
            AuthenticationError: If the token is invalid, used or expired.
            ValueError: If the new password does not meet the policy.

        """
        token_hash = hash_token(token)
        invalid = AuthenticationError("Invalid or expired reset token")

        record = await self.data_service.database_service.get_record(
            "password_reset_tokens", {"token_hash": token_hash, "used_at": None}
        )
        expires_at = record.get("expires_at") if record else None
        if not record or not isinstance(expires_at, datetime):
            raise invalid
        if expires_at < datetime.now(UTC):
            raise invalid

        self.password_service.assert_password_strength(new_password)

        # Consume atomically: of two concurrent confirmations only one matches
        # ``used_at: None`` and proceeds.
        consumed = await self.data_service.update(
            "password_reset_tokens",
            {"token_hash": token_hash, "used_at": None},
            {"used_at": datetime.now(UTC)},
            policy=CachePolicy.DB_ONLY,
        )
        if not consumed:
            raise invalid

        user_id = record["user_id"]
        updated = await self.data_service.users.update_user(
            user_id,
            {
                "password": await self.password_service.ahash_password(new_password),
                "failed_login_count": 0,
                "locked_until": None,
                "email_verified": True,  # the reset link went to this address
            },
        )
        if not updated:
            raise invalid

        await self.sessions.revoke_user_sessions(user_id)
        await self.audit.record(
            "user.password_reset", target_type="user", target_id=user_id, actor_id=user_id
        )
        self.logger.info(
            "Password reset completed",
            extra={"service": "AuthService", "user_id": user_id},
        )
        return True


__all__ = ["AuthService", "AuthenticationError", "MFAError", "MFARequiredError"]
