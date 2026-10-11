"""One OpenID Connect client that works with any compliant identity provider.

Google, Microsoft Entra ID, Okta, Auth0, Keycloak, GitLab and others differ only in
configuration: give a provider its ``issuer`` and the endpoints come from discovery
(``/.well-known/openid-configuration``). Each sign-in uses the authorization-code flow with:

* **PKCE (S256)**: a stolen authorization code is useless without this browser's verifier;
* **a nonce**: an ID token minted for another sign-in is refused;
* **ID-token verification**: signature against the provider's published keys (asymmetric
  algorithms only), issuer, audience (our client id), expiry, then the nonce.

Every outbound call has a timeout. Providers without an ID token (plain OAuth 2.0) fall back to
the userinfo endpoint over TLS.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import secrets
import urllib.parse
from dataclasses import dataclass
from typing import Any

import httpx
import jwt

from app.models.oauth import OAuthUserInfo

ALLOWED_ALGORITHMS = {"RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256", "ES384"}
DEFAULT_SCOPES = ["openid", "email", "profile"]
CLOCK_SKEW_SECONDS = 60


class OIDCError(ValueError):
    """The provider's answer could not be trusted; the message is safe to log, not to show."""


@dataclass(frozen=True)
class SignInAttempt:
    """What one browser must present again at the callback (kept in an HttpOnly cookie)."""

    state: str
    code_verifier: str
    nonce: str

    def pack(self) -> str:
        return f"{self.state}.{self.code_verifier}.{self.nonce}"

    @classmethod
    def unpack(cls, value: str | None) -> SignInAttempt | None:
        parts = (value or "").split(".")
        return cls(*parts) if len(parts) == 3 and all(parts) else None

    @classmethod
    def new(cls) -> SignInAttempt:
        return cls(secrets.token_urlsafe(32), secrets.token_urlsafe(64), secrets.token_urlsafe(32))


def _challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


class OIDCClient:
    """One configured provider: ``[oauth_providers.<name>]`` in config.toml."""

    def __init__(
        self,
        name: str,
        settings: dict[str, Any],
        *,
        timeout: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        missing = [
            key for key in ("client_id", "client_secret", "redirect_uri") if not settings.get(key)
        ]
        manual = all(settings.get(k) for k in ("authorization_url", "token_url", "userinfo_url"))
        if not settings.get("issuer") and not manual:
            missing.append("issuer (or authorization_url, token_url and userinfo_url)")
        if missing:
            raise ValueError(f"oauth_providers.{name} needs {', '.join(missing)}")
        self.name = name
        self.settings = settings
        self.trust_email = bool(settings.get("trust_email", False))
        self.scopes = list(settings.get("scopes") or DEFAULT_SCOPES)
        self._http = {"timeout": timeout, "transport": transport}
        self._metadata: dict[str, Any] | None = None
        self._keys: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(**self._http)

    # ---- discovery ---------------------------------------------------------------------
    async def metadata(self) -> dict[str, Any]:
        """Endpoints: discovered once from ``issuer``, overridable per setting."""
        if self._metadata is None:
            async with self._lock:
                if self._metadata is None:
                    discovered: dict[str, Any] = {}
                    issuer = self.settings.get("issuer")
                    if issuer:
                        url = issuer.rstrip("/") + "/.well-known/openid-configuration"
                        async with self._client() as client:
                            response = await client.get(url)
                            response.raise_for_status()
                            discovered = response.json()
                        if discovered.get("issuer", "").rstrip("/") != issuer.rstrip("/"):
                            raise OIDCError(f"{self.name}: discovery issuer does not match")
                    overrides = {
                        "authorization_endpoint": self.settings.get("authorization_url"),
                        "token_endpoint": self.settings.get("token_url"),
                        "userinfo_endpoint": self.settings.get("userinfo_url"),
                        "jwks_uri": self.settings.get("jwks_uri"),
                    }
                    self._metadata = {**discovered, **{k: v for k, v in overrides.items() if v}}
        return self._metadata

    # ---- the flow ----------------------------------------------------------------------
    async def authorization_url(self, attempt: SignInAttempt) -> str:
        meta = await self.metadata()
        params = {
            "client_id": self.settings["client_id"],
            "redirect_uri": self.settings["redirect_uri"],
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": attempt.state,
            "nonce": attempt.nonce,
            "code_challenge": _challenge(attempt.code_verifier),
            "code_challenge_method": "S256",
            **self.settings.get("extra_authorize_params", {}),
        }
        return f"{meta['authorization_endpoint']}?{urllib.parse.urlencode(params)}"

    async def identity(self, code: str, attempt: SignInAttempt) -> OAuthUserInfo:
        """Exchange the code and return who signed in, verified."""
        meta = await self.metadata()
        async with self._client() as client:
            response = await client.post(
                meta["token_endpoint"],
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.settings["redirect_uri"],
                    "client_id": self.settings["client_id"],
                    "client_secret": self.settings["client_secret"],
                    "code_verifier": attempt.code_verifier,
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            tokens = response.json()
            if tokens.get("id_token"):
                claims = await self._verify_id_token(tokens["id_token"], attempt.nonce)
            elif meta.get("userinfo_endpoint") and tokens.get("access_token"):
                info = await client.get(
                    meta["userinfo_endpoint"],
                    headers={"Authorization": f"Bearer {tokens['access_token']}"},
                )
                info.raise_for_status()
                claims = info.json()
            else:
                raise OIDCError(f"{self.name}: no ID token and no userinfo endpoint")
        return self._user_info(claims)

    def _user_info(self, claims: dict[str, Any]) -> OAuthUserInfo:
        if not claims.get("sub"):
            raise OIDCError(f"{self.name}: identity has no subject")
        verified = claims.get("email_verified")
        verified = verified is True or str(verified).lower() == "true"
        return OAuthUserInfo(
            provider_user_id=str(claims["sub"]),
            email=claims.get("email"),
            email_verified=bool(claims.get("email")) and (verified or self.trust_email),
            name=claims.get("name") or claims.get("preferred_username") or "",
            picture=claims.get("picture"),
        )

    # ---- ID tokens ---------------------------------------------------------------------
    async def _signing_key(self, kid: str | None, refresh: bool = False) -> Any:
        if refresh or not self._keys:
            meta = await self.metadata()
            if not meta.get("jwks_uri"):
                raise OIDCError(f"{self.name}: no jwks_uri to verify ID tokens")
            async with self._client() as client:
                response = await client.get(meta["jwks_uri"])
                response.raise_for_status()
            keys = jwt.PyJWKSet.from_dict(response.json()).keys
            self._keys = {key.key_id: key for key in keys}
        if kid in self._keys:
            return self._keys[kid]
        if kid is None and len(self._keys) == 1:
            return next(iter(self._keys.values()))
        if not refresh:  # the provider rotated its keys since we cached them
            return await self._signing_key(kid, refresh=True)
        raise OIDCError(f"{self.name}: ID token signed with an unknown key")

    async def _verify_id_token(self, id_token: str, nonce: str) -> dict[str, Any]:
        meta = await self.metadata()
        try:
            header = jwt.get_unverified_header(id_token)
        except jwt.InvalidTokenError as e:
            raise OIDCError(f"{self.name}: malformed ID token") from e
        offered = set(meta.get("id_token_signing_alg_values_supported") or ["RS256"])
        algorithm = header.get("alg")
        if algorithm not in ALLOWED_ALGORITHMS & offered:
            raise OIDCError(f"{self.name}: ID token algorithm {algorithm!r} is not allowed")
        key = await self._signing_key(header.get("kid"))
        try:
            claims = jwt.decode(
                id_token,
                key.key,
                algorithms=[algorithm],
                audience=self.settings["client_id"],
                issuer=meta.get("issuer") or self.settings.get("issuer"),
                leeway=CLOCK_SKEW_SECONDS,
                options={"require": ["exp", "iat", "sub", "iss", "aud"]},
            )
        except jwt.InvalidTokenError as e:
            raise OIDCError(f"{self.name}: ID token rejected ({e})") from e
        if not hmac.compare_digest(str(claims.get("nonce", "")), nonce):
            raise OIDCError(f"{self.name}: ID token nonce does not match this sign-in")
        return claims
