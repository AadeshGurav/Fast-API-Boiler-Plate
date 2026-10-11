"""Sign-in with external identity providers, and linking them to local accounts."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.models.oauth import OAuthAccount, OAuthUserInfo
from app.models.user import User, UserRole
from app.services.base_service import BaseService
from app.services.oauth.oidc import OIDCClient, SignInAttempt

if TYPE_CHECKING:
    import httpx

    from app.services.audit import AuditService
    from app.services.data import DataService
    from app.services.logger import Logger
    from config import Config


class UnknownProviderError(LookupError):
    """No provider with this name is configured."""


class OAuthService(BaseService):
    """Every ``[oauth_providers.<name>]`` becomes an OpenID Connect client."""

    def __init__(
        self,
        config: Config,
        logger: Logger,
        data_service: DataService,
        audit: AuditService,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(config, logger)
        self.data_service = data_service
        self.audit = audit
        self.oauth_enabled: bool = config["oauth_enabled"]
        self.providers: dict[str, OIDCClient] = {
            name: OIDCClient(
                name, settings, timeout=config["oauth_timeout_seconds"], transport=transport
            )
            for name, settings in config["oauth_providers"].items()
        }

    def provider(self, name: str) -> OIDCClient:
        if name not in self.providers:
            raise UnknownProviderError(f"Unknown sign-in provider: {name}")
        return self.providers[name]

    async def begin(self, name: str) -> tuple[str, SignInAttempt]:
        """The provider URL to send the browser to, and what it must bring back."""
        attempt = SignInAttempt.new()
        return await self.provider(name).authorization_url(attempt), attempt

    async def complete(self, name: str, code: str, attempt: SignInAttempt) -> User:
        """Verify the provider's answer and return the local account it signs in."""
        info = await self.provider(name).identity(code, attempt)
        return await self.create_or_link_user(info, name)

    # ---- account linking -----------------------------------------------------------------
    async def create_or_link_user(self, info: OAuthUserInfo, provider: str) -> User:
        """The account already linked to this identity, else the verified-email owner, else a
        new account."""
        existing = await self.data_service.oauth.get_oauth_account(provider, info.provider_user_id)
        if existing:
            user = await self.data_service.users.get_user_by_id(existing["user_id"])
            if user:
                return User(**user)

        # Everything below identifies a person by email, which is only safe if the provider
        # vouches that the user owns it. Otherwise anyone could register an IdP account with
        # a victim's address and take over the victim's local account.
        if not info.email or not info.email_verified:
            raise ValueError("Your account must have a verified email address to sign in this way.")

        local = await self.data_service.users.get_user_by_email(info.email)
        if local:
            if not local.get("email_verified"):
                # Local sign-up never proved the address. Whoever registered it first may not
                # be its owner, so the password and sessions they hold must not survive the
                # real owner signing in (account pre-hijacking).
                await self.data_service.users.update_user(
                    local["id"], {"password": None, "password_hash": None, "email_verified": True}
                )
                await self.data_service.sessions.revoke_user_sessions(local["id"])
                local = {**local, "password_hash": None, "email_verified": True}
            await self._link(local["id"], provider, info)
            return User(**local)

        username = await self._unique_username(info.email.split("@")[0])
        user_id = await self.data_service.users.create_user(
            {
                "username": username,
                "email": info.email,
                "email_verified": True,
                "roles": [UserRole.USER.value],
                "groups": [],
                "status": "active",
                "profile": {"name": info.name},
                "failed_login_count": 0,
                "locked_until": None,
                "last_login": datetime.now(UTC),
                # No password: the account can only be entered through its provider.
            }
        )
        user = User(**await self.data_service.users.get_user_by_id(user_id))
        await self._link(user.id, provider, info)
        await self.audit.record(
            "user.registered",
            target_type="user",
            target_id=user.id,
            actor_id=user.id,
            details={"provider": provider},
        )
        return user

    async def _link(self, user_id: str, provider: str, info: OAuthUserInfo) -> None:
        """Record the provider identity. Provider tokens are deliberately not stored: nothing
        here calls the provider again, and stored tokens would only be a liability."""
        account = OAuthAccount(
            user_id=user_id, provider=provider, provider_user_id=info.provider_user_id
        )
        await self.data_service.oauth.link_oauth_account(account.model_dump())
        await self.audit.record(
            "oauth.linked",
            target_type="user",
            target_id=user_id,
            actor_id=user_id,
            details={"provider": provider},
        )

    async def _unique_username(self, base: str) -> str:
        """First free username of ``base``, ``base_1``, ``base_2``, ..."""
        base = (base or f"user_{secrets.token_hex(4)}")[:40].ljust(3, "_")
        candidate, counter = base, 0
        while await self.data_service.users.get_user_by_username(candidate):
            counter += 1
            candidate = f"{base}_{counter}"
        return candidate

    async def unlink_oauth_account(self, user_id: str, provider: str) -> bool:
        unlinked = await self.data_service.oauth.unlink_oauth_account(user_id, provider)
        if unlinked:
            await self.audit.record(
                "oauth.unlinked",
                target_type="user",
                target_id=user_id,
                details={"provider": provider},
            )
        return unlinked

    def describe(self) -> list[dict[str, Any]]:
        """Configured providers, for a sign-in screen (names only, never secrets)."""
        return [{"name": name} for name in self.providers]
