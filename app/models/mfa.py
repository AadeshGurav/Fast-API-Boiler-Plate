"""Two-factor authentication requests and responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MFAStatus(BaseModel):
    totp_enabled: bool = Field(..., description="Whether sign-in asks for an authenticator code")
    recovery_codes_left: int = Field(..., description="Unused recovery codes")


class PasswordConfirmation(BaseModel):
    password: str = Field(..., min_length=1, max_length=1024, description="Current password")


class MFACode(BaseModel):
    code: str = Field(
        ..., min_length=6, max_length=32, description="Authenticator code or recovery code"
    )


class PasswordAndCode(PasswordConfirmation, MFACode):
    """Sensitive changes need both what the user knows and what they have."""


class TOTPSetup(BaseModel):
    secret: str = Field(..., description="Base32 secret, for manual entry in the app")
    otpauth_uri: str = Field(..., description="Render as a QR code for the authenticator app")


class RecoveryCodes(BaseModel):
    recovery_codes: list[str] = Field(
        ..., description="Shown once: each code signs in once when the phone is unavailable"
    )


class MFALoginRequest(MFACode):
    mfa_token: str = Field(..., max_length=2048, description="From the mfa_required problem")
