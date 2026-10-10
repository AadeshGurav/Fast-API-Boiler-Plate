"""Multi-factor authentication: authenticator-app codes (TOTP) and single-use recovery codes.

The shared secret is encrypted at rest with ``mfa_encryption_key`` (Fernet), lives in its own
``mfa_totp`` collection (never on the cached user record), and is read from the database only.
Accepting a code is a conditional update on the last accepted time step, so a code works once
even when two requests race. Recovery codes are stored hashed and consumed the same way.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from cryptography.fernet import Fernet

from app.services.auth.totp import generate_secret, matching_step, provisioning_uri
from app.services.data.policies import CachePolicy
from app.services.data.sessions_ops import hash_token

if TYPE_CHECKING:
    from app.services.audit import AuditService
    from app.services.data import DataService
    from app.services.logger import Logger
    from app.services.password_service import PasswordService
    from config import Config

COLLECTION = "mfa_totp"
DB = CachePolicy.DB_ONLY


class MFAError(ValueError):
    """A second-factor step was refused; the message is safe to show."""


class MFAStateError(MFAError):
    """The request does not fit the current MFA state (already on, not set up...)."""


def _fernet(key: str) -> Fernet:
    # Any string works as the configured key: it is stretched to the 32 bytes Fernet needs.
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest()))


def _new_recovery_codes(count: int) -> list[str]:
    alphabet = "abcdefghjkmnpqrstuvwxyz23456789"  # no 0/o, 1/l/i: easy to read and type
    return [
        "-".join("".join(secrets.choice(alphabet) for _ in range(5)) for _ in range(2))
        for _ in range(count)
    ]


def _normalize_recovery_code(code: str) -> str:
    return code.strip().lower().replace(" ", "")


class MFAService:
    """Enrol, verify and remove a user's second factor."""

    def __init__(
        self,
        config: Config,
        logger: Logger,
        data_service: DataService,
        password_service: PasswordService,
        audit: AuditService,
    ) -> None:
        self.config = config
        self.logger = logger
        self.data_service = data_service
        self.password_service = password_service
        self.audit = audit
        self.fernet = _fernet(config["mfa_encryption_key"] or "")
        self.issuer: str = config["mfa_issuer"] or config["app_title"]
        self.recovery_code_count: int = config["mfa_recovery_codes"]

    # ---- state -----------------------------------------------------------------------
    async def _factor(self, user_id: str) -> dict[str, Any] | None:
        return await self.data_service.get(COLLECTION, {"user_id": user_id}, policy=DB)

    async def is_enabled(self, user_id: str) -> bool:
        factor = await self._factor(user_id)
        return bool(factor and factor.get("confirmed_at"))

    async def status(self, user_id: str) -> dict[str, Any]:
        factor = await self._factor(user_id)
        enabled = bool(factor and factor.get("confirmed_at"))
        return {
            "totp_enabled": enabled,
            "recovery_codes_left": len(factor.get("recovery_codes", [])) if enabled else 0,
        }

    async def _check_password(self, user_id: str, password: str) -> dict[str, Any]:
        user = await self.data_service.users.get_user_by_id(user_id, fresh=True)
        if not user or not await self.password_service.averify_password(
            password, user.get("password_hash") or ""
        ):
            raise MFAError("Current password is incorrect")
        return user

    # ---- enrolment ---------------------------------------------------------------------
    async def start_totp(self, user_id: str, password: str) -> dict[str, str]:
        """Create (or replace an unconfirmed) secret; returns it and its ``otpauth://`` URI."""
        user = await self._check_password(user_id, password)
        if await self.is_enabled(user_id):
            raise MFAStateError("Two-factor authentication is already on; turn it off first")
        secret = generate_secret()
        await self.data_service.set(
            COLLECTION,
            {"user_id": user_id},
            {
                "secret": self.fernet.encrypt(secret.encode()).decode(),
                "confirmed_at": None,
                "last_step": 0,
                "recovery_codes": [],
                "codes_version": 0,
                "created_at": datetime.now(UTC),
            },
            policy=DB,
        )
        account = user.get("email") or user["username"]
        return {
            "secret": secret,
            "otpauth_uri": provisioning_uri(secret, account, self.issuer),
        }

    async def confirm_totp(self, user_id: str, code: str) -> list[str]:
        """Turn MFA on once the user proves their app works; returns new recovery codes."""
        factor = await self._factor(user_id)
        if not factor or factor.get("confirmed_at"):
            raise MFAStateError("Start setting up two-factor authentication first")
        if not await self._accept_totp(factor, code):
            raise MFAError("The code is not valid")
        codes = _new_recovery_codes(self.recovery_code_count)
        await self.data_service.update(
            COLLECTION,
            {"user_id": user_id},
            {
                "confirmed_at": datetime.now(UTC),
                "recovery_codes": [hash_token(c) for c in codes],
                "codes_version": factor.get("codes_version", 0) + 1,
            },
            policy=DB,
        )
        await self.audit.record("mfa.enabled", target_type="user", target_id=user_id)
        return codes

    async def disable(self, user_id: str, password: str, code: str) -> None:
        """Turn MFA off; needs the password and a current code (or a recovery code)."""
        await self._check_password(user_id, password)
        if not await self.is_enabled(user_id):
            raise MFAStateError("Two-factor authentication is not on")
        if not await self.verify(user_id, code):
            raise MFAError("The code is not valid")
        await self.data_service.delete(COLLECTION, {"user_id": user_id}, policy=DB)
        await self.audit.record("mfa.disabled", target_type="user", target_id=user_id)

    async def regenerate_recovery_codes(self, user_id: str, password: str, code: str) -> list[str]:
        """Replace every recovery code (the old ones stop working)."""
        await self._check_password(user_id, password)
        if not await self.is_enabled(user_id):
            raise MFAStateError("Two-factor authentication is not on")
        if not await self.verify(user_id, code):
            raise MFAError("The code is not valid")
        codes = _new_recovery_codes(self.recovery_code_count)
        factor = await self._factor(user_id) or {}
        await self.data_service.update(
            COLLECTION,
            {"user_id": user_id},
            {
                "recovery_codes": [hash_token(c) for c in codes],
                "codes_version": factor.get("codes_version", 0) + 1,
            },
            policy=DB,
        )
        await self.audit.record(
            "mfa.recovery_codes_regenerated", target_type="user", target_id=user_id
        )
        return codes

    async def reset(self, user_id: str) -> bool:
        """Administrator recovery for a user who lost both phone and recovery codes."""
        removed = await self.data_service.delete(COLLECTION, {"user_id": user_id}, policy=DB)
        if removed:
            await self.audit.record("mfa.reset", target_type="user", target_id=user_id)
        return removed

    # ---- verification ------------------------------------------------------------------
    async def verify(self, user_id: str, code: str) -> bool:
        """True if ``code`` is a valid, unused authenticator code or recovery code."""
        factor = await self._factor(user_id)
        if not factor or not factor.get("confirmed_at"):
            return False
        if await self._accept_totp(factor, code):
            return True
        return await self._consume_recovery_code(factor, code)

    async def _accept_totp(self, factor: dict[str, Any], code: str) -> bool:
        secret = self.fernet.decrypt(factor["secret"].encode()).decode()
        step = matching_step(secret, code)
        last = factor.get("last_step", 0)
        if step is None or step <= last:
            return False
        # Conditional on the step we read: of two requests racing with one code, one wins.
        return await self.data_service.update(
            COLLECTION,
            {"user_id": factor["user_id"], "last_step": last},
            {"last_step": step},
            policy=DB,
        )

    async def _consume_recovery_code(self, factor: dict[str, Any], code: str) -> bool:
        hashed = hash_token(_normalize_recovery_code(code))
        remaining = list(factor.get("recovery_codes", []))
        if hashed not in remaining:
            return False
        remaining.remove(hashed)
        # Conditional on the list being the one we read (its version), so a code works once
        # and two different codes used at the same moment cannot resurrect each other.
        version = factor.get("codes_version", 0)
        used = await self.data_service.update(
            COLLECTION,
            {"user_id": factor["user_id"], "codes_version": version},
            {"recovery_codes": remaining, "codes_version": version + 1},
            policy=DB,
        )
        if used:
            await self.audit.record(
                "mfa.recovery_code_used",
                target_type="user",
                target_id=factor["user_id"],
                details={"recovery_codes_left": len(remaining)},
            )
        return used
