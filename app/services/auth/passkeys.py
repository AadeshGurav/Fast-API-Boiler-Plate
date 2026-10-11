"""Passkeys (WebAuthn): sign-in with Face ID, Touch ID, Windows Hello or a security key.

A passkey is a key pair made by the user's device for this site (``webauthn_rp_id``); only the
public key is stored here. The browser will only use it on the configured origins, so it
cannot be phished, and signing in requires user verification (biometric or device PIN), so a
passkey sign-in is itself multi-factor and skips the authenticator-code step.

Each ceremony uses a single-use challenge kept in ``webauthn_challenges`` (five minutes, deleted
on use, expired by a time-to-live index), so a captured response cannot be replayed.
"""

from __future__ import annotations

import base64
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import webauthn
from webauthn.helpers import bytes_to_base64url
from webauthn.helpers.exceptions import InvalidAuthenticationResponse, InvalidRegistrationResponse
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.core.interfaces.database_interface import DuplicateRecordError
from app.services.data.policies import CachePolicy

if TYPE_CHECKING:
    from app.services.audit import AuditService
    from app.services.data import DataService
    from config import Config

PASSKEYS = "passkeys"
CHALLENGES = "webauthn_challenges"
DB = CachePolicy.DB_ONLY
CHALLENGE_LIFETIME = timedelta(minutes=5)
MAX_PASSKEYS_PER_USER = 20


class PasskeyError(ValueError):
    """A passkey ceremony was refused; the message is safe to show."""


class PasskeysDisabledError(PasskeyError):
    """``passkeys_enabled`` is off or the relying party is not configured."""


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def public_view(record: dict[str, Any]) -> dict[str, Any]:
    return {k: record.get(k) for k in ("id", "name", "created_at", "last_used_at", "transports")}


class PasskeyManager:
    """Register, list, remove and verify passkeys."""

    def __init__(self, config: Config, data_service: DataService, audit: AuditService) -> None:
        self.data_service = data_service
        self.audit = audit
        self.enabled = bool(config["passkeys_enabled"])
        self.rp_id: str = config["webauthn_rp_id"]
        self.rp_name: str = config["webauthn_rp_name"] or config["app_title"]
        self.origins: list[str] = list(config["webauthn_origins"])

    def _require_enabled(self) -> None:
        if not (self.enabled and self.rp_id and self.origins):
            raise PasskeysDisabledError("Passkeys are not configured on this server")

    # ---- single-use challenges -------------------------------------------------------------
    async def _issue_challenge(self, purpose: str, user_id: str | None) -> tuple[str, bytes]:
        challenge = secrets.token_bytes(32)
        challenge_id = uuid.uuid4().hex
        await self.data_service.insert(
            CHALLENGES,
            {
                "id": challenge_id,
                "purpose": purpose,
                "user_id": user_id,
                "challenge": bytes_to_base64url(challenge),
                "expires_at": datetime.now(UTC) + CHALLENGE_LIFETIME,
            },
        )
        return challenge_id, challenge

    async def _consume_challenge(
        self, challenge_id: str, purpose: str, user_id: str | None
    ) -> bytes:
        record = await self.data_service.get(CHALLENGES, {"id": challenge_id}, policy=DB)
        # Deleted before checking: whatever the outcome, this challenge is spent.
        if not record or not await self.data_service.delete(
            CHALLENGES, {"id": challenge_id}, policy=DB
        ):
            raise PasskeyError("This passkey request expired; start again")
        if (
            record["purpose"] != purpose
            or record.get("user_id") != user_id
            or record["expires_at"] < datetime.now(UTC)
        ):
            raise PasskeyError("This passkey request expired; start again")
        return _b64url_decode(record["challenge"])

    # ---- registration ----------------------------------------------------------------------
    async def registration_options(self, user: dict[str, Any]) -> dict[str, Any]:
        self._require_enabled()
        existing = await self._for_user(user["id"])
        if len(existing) >= MAX_PASSKEYS_PER_USER:
            raise PasskeyError(
                f"You already have {MAX_PASSKEYS_PER_USER} passkeys; remove one first"
            )
        challenge_id, challenge = await self._issue_challenge("register", user["id"])
        options = webauthn.generate_registration_options(
            rp_id=self.rp_id,
            rp_name=self.rp_name,
            user_id=user["id"].encode(),
            user_name=user["username"],
            user_display_name=user.get("email") or user["username"],
            challenge=challenge,
            exclude_credentials=[
                PublicKeyCredentialDescriptor(id=_b64url_decode(p["credential_id"]))
                for p in existing
            ],
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.REQUIRED,  # usable without typing a username
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
        )
        return {
            "challenge_id": challenge_id,
            "options": json.loads(webauthn.options_to_json(options)),
        }

    async def register(
        self, user_id: str, challenge_id: str, credential: dict[str, Any], name: str
    ) -> dict[str, Any]:
        self._require_enabled()
        challenge = await self._consume_challenge(challenge_id, "register", user_id)
        try:
            verified = webauthn.verify_registration_response(
                credential=credential,
                expected_challenge=challenge,
                expected_rp_id=self.rp_id,
                expected_origin=self.origins,
                require_user_verification=True,
            )
        except InvalidRegistrationResponse as e:
            raise PasskeyError("The passkey could not be verified") from e
        record = {
            "id": uuid.uuid4().hex,
            "user_id": user_id,
            "name": name,
            "credential_id": bytes_to_base64url(verified.credential_id),
            "public_key": bytes_to_base64url(verified.credential_public_key),
            "sign_count": verified.sign_count,
            "transports": (credential.get("response") or {}).get("transports") or [],
            "created_at": datetime.now(UTC),
            "last_used_at": None,
        }
        try:
            await self.data_service.insert(PASSKEYS, record)
        except DuplicateRecordError as e:
            raise PasskeyError("This passkey is already registered") from e
        await self.audit.record(
            "passkey.added",
            target_type="user",
            target_id=user_id,
            details={"passkey_id": record["id"]},
        )
        return public_view(record)

    # ---- management ------------------------------------------------------------------------
    async def _for_user(self, user_id: str) -> list[dict[str, Any]]:
        return await self.data_service.find_many(
            PASSKEYS,
            {"user_id": user_id},
            policy=DB,
            sort=[("created_at", -1)],
            limit=MAX_PASSKEYS_PER_USER,
        )

    async def list_for(self, user_id: str) -> list[dict[str, Any]]:
        return [public_view(p) for p in await self._for_user(user_id)]

    async def remove(self, user_id: str, passkey_id: str) -> bool:
        removed = await self.data_service.delete(
            PASSKEYS, {"id": passkey_id, "user_id": user_id}, policy=DB
        )
        if removed:
            await self.audit.record(
                "passkey.removed",
                target_type="user",
                target_id=user_id,
                details={"passkey_id": passkey_id},
            )
        return removed

    # ---- sign-in ---------------------------------------------------------------------------
    async def authentication_options(self) -> dict[str, Any]:
        self._require_enabled()
        challenge_id, challenge = await self._issue_challenge("login", None)
        options = webauthn.generate_authentication_options(
            rp_id=self.rp_id,
            challenge=challenge,
            user_verification=UserVerificationRequirement.REQUIRED,
        )
        return {
            "challenge_id": challenge_id,
            "options": json.loads(webauthn.options_to_json(options)),
        }

    async def authenticate(self, challenge_id: str, credential: dict[str, Any]) -> str:
        """Verify a sign-in; returns the user id the passkey belongs to."""
        self._require_enabled()
        challenge = await self._consume_challenge(challenge_id, "login", None)
        passkey = await self.data_service.get(
            PASSKEYS, {"credential_id": str(credential.get("id", ""))}, policy=DB
        )
        if passkey is None:
            raise PasskeyError("This passkey is not registered here")
        try:
            verified = webauthn.verify_authentication_response(
                credential=credential,
                expected_challenge=challenge,
                expected_rp_id=self.rp_id,
                expected_origin=self.origins,
                credential_public_key=_b64url_decode(passkey["public_key"]),
                credential_current_sign_count=passkey.get("sign_count", 0),
                require_user_verification=True,
            )
        except InvalidAuthenticationResponse as e:
            raise PasskeyError("The passkey could not be verified") from e
        await self.data_service.update(
            PASSKEYS,
            {"id": passkey["id"]},
            {"sign_count": verified.new_sign_count, "last_used_at": datetime.now(UTC)},
            policy=DB,
        )
        return passkey["user_id"]
