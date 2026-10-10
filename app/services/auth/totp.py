"""Time-based one-time passwords (RFC 6238), standard library only.

The codes authenticator apps (Google Authenticator, 1Password, Authy...) show: HMAC-SHA1 over
the number of 30-second steps since the epoch, truncated to six digits (RFC 4226).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote, urlencode

STEP_SECONDS = 30
DIGITS = 6
SECRET_BYTES = 20  # 160 bits, the size RFC 4226 recommends for HMAC-SHA1


def generate_secret() -> str:
    """A new random shared secret, base32 encoded as authenticator apps expect."""
    return base64.b32encode(secrets.token_bytes(SECRET_BYTES)).decode("ascii")


def current_step(now: float | None = None) -> int:
    return int((time.time() if now is None else now) // STEP_SECONDS)


def code_at(secret: str, step: int) -> str:
    """The code for one time step."""
    key = base64.b32decode(secret.upper() + "=" * (-len(secret) % 8))
    digest = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(number % 10**DIGITS).zfill(DIGITS)


def matching_step(
    secret: str, code: str, *, window: int = 1, now: float | None = None
) -> int | None:
    """The time step ``code`` belongs to, allowing ``window`` steps of clock skew either way,
    or None. Callers must refuse a step at or before the last one accepted (replay)."""
    code = code.strip().replace(" ", "")
    if len(code) != DIGITS or not code.isdigit():
        return None
    step = current_step(now)
    for candidate in range(step - window, step + window + 1):
        if hmac.compare_digest(code_at(secret, candidate), code):
            return candidate
    return None


def provisioning_uri(secret: str, account: str, issuer: str) -> str:
    """The ``otpauth://`` URI a client renders as a QR code."""
    label = quote(f"{issuer}:{account}")
    query = urlencode(
        {"secret": secret, "issuer": issuer, "digits": DIGITS, "period": STEP_SECONDS}
    )
    return f"otpauth://totp/{label}?{query}"
