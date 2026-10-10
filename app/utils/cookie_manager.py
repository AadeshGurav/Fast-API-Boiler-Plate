"""Centralized cookie management for authentication tokens."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.models.auth import TokenPair

if TYPE_CHECKING:
    from fastapi import Response

    from config import Config


def get_token_cookie_names(config: Config) -> tuple[str, str]:
    """Access and refresh token cookie names (namespaced by the app title)."""
    prefix = config["app_title"].lower().replace(" ", "_")
    return f"{prefix}_access_token", f"{prefix}_refresh_token"


def default_cookie_secure(config: Config | None) -> bool:
    """Whether cookies get the Secure flag: on, except explicit config or debug mode."""
    if config is None:
        return True
    return config["cookie_secure"]


class CookieManager:
    """Reads cookie policy from config and applies it to auth cookies.

    Secure by default: tokens are HttpOnly (the server reads them from the cookie, so
    scripts never need to) and Secure unless the app runs in debug over plain HTTP.
    """

    @staticmethod
    def _policy(config: Config | None) -> dict[str, object]:
        return {
            "httponly": config["cookie_httponly"] if config else True,
            "secure": default_cookie_secure(config),
            "samesite": config["cookie_samesite"] if config else "lax",
            "path": "/",
        }

    @staticmethod
    def set_auth_cookies(
        response: Response,
        token_pair: TokenPair,
        config: Config | None = None,
        remember_me: bool = False,
    ) -> None:
        """Set the access and refresh token cookies.

        Args:
        ----
            response: Response to attach the cookies to.
            token_pair: Access and refresh tokens.
            config: Configuration for cookie policy.
            remember_me: If True, the refresh cookie lasts 30 days instead of 7.

        """
        access_token_key, refresh_token_key = get_token_cookie_names(config)
        policy = CookieManager._policy(config)
        refresh_days = config["remember_me_days"] if remember_me else config["refresh_token_days"]

        response.set_cookie(
            key=access_token_key,
            value=token_pair.access_token,
            max_age=token_pair.expires_in,
            **policy,
        )
        response.set_cookie(
            key=refresh_token_key,
            value=token_pair.refresh_token,
            max_age=refresh_days * 24 * 60 * 60,
            **policy,
        )

    @staticmethod
    def delete_auth_cookies(response: Response, config: Config) -> None:
        """Remove both authentication cookies."""
        access_token_key, refresh_token_key = get_token_cookie_names(config)
        response.delete_cookie(key=access_token_key, path="/")
        response.delete_cookie(key=refresh_token_key, path="/")


__all__ = ["CookieManager", "default_cookie_secure", "get_token_cookie_names"]
