"""Centralized cookie management for authentication tokens."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Response
from fastapi.responses import JSONResponse

from app.models.auth import TokenPair
from app.utils.permissions import get_token_cookie_names

if TYPE_CHECKING:
    from config import Config


class CookieManager:
    """Centralized manager for authentication cookie operations."""

    @staticmethod
    def set_auth_cookies(
        response: Response | JSONResponse,
        token_pair: TokenPair,
        config: Config | None = None,
        remember_me: bool = False,
    ) -> None:
        """Set authentication cookies from a TokenPair.

        Args:
        ----
            response: FastAPI response object
            token_pair: TokenPair containing access and refresh tokens
            config: Configuration instance for cookie settings (optional)
            remember_me: If True, set refresh token cookie to 30 days

        """
        access_token_key, refresh_token_key = get_token_cookie_names()

        # Get cookie security settings from config
        # For development: default to False for secure (allows HTTP) and httponly (allows JS access)
        # For production: should be set to True in config
        if config:
            httponly = config.get(
                "cookie_httponly", False
            )  # Default False for development
            secure = config.get(
                "cookie_secure", False
            )  # Default False for HTTP (localhost)
            samesite = config.get("cookie_samesite", "lax")
        else:
            # Development-friendly defaults if no config provided
            httponly = False
            secure = False  # Allow HTTP (localhost)
            samesite = "lax"

        if token_pair.access_token:
            response.set_cookie(
                key=access_token_key,
                value=token_pair.access_token,
                max_age=token_pair.expires_in,
                httponly=httponly,
                samesite=samesite,
                secure=secure,
                path="/",
            )

        if token_pair.refresh_token:
            # Set refresh token cookie expiry: 30 days if remember_me, otherwise 7 days
            refresh_max_age = 30 * 24 * 60 * 60 if remember_me else 7 * 24 * 60 * 60
            response.set_cookie(
                key=refresh_token_key,
                value=token_pair.refresh_token,
                max_age=refresh_max_age,
                httponly=httponly,
                samesite=samesite,
                secure=secure,
                path="/",
            )

    @staticmethod
    def set_token_cookies(
        response: Response | JSONResponse,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        config: Config | None = None,
        remember_me: bool = False,
    ) -> None:
        """Set authentication cookies from individual tokens.

        Args:
        ----
            response: FastAPI response object
            access_token: JWT access token
            refresh_token: JWT refresh token
            expires_in: Access token expiration in seconds
            config: Configuration instance for cookie settings (optional)
            remember_me: If True, set refresh token cookie to 30 days

        """
        token_pair = TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )
        CookieManager.set_auth_cookies(response, token_pair, config, remember_me)

    @staticmethod
    def set_session_cookie(
        response: Response | JSONResponse,
        session_id: str,
        config: Config | None = None,
        remember_me: bool = False,
    ) -> None:
        """Set session cookie in response.

        Args:
        ----
            response: FastAPI response object
            session_id: Session ID to set
            config: Configuration instance for cookie settings (optional)
            remember_me: If True, set cookie max_age to 30 days

        """
        # Get cookie settings from config
        # For development: default to False for secure (allows HTTP) and httponly (allows JS access)
        if config:
            cookie_name = config.get("auth_session_cookie_name", "auth_session")
            default_max_age = config.get("session_max_age", 7 * 24 * 60 * 60)  # 7 days
            path = config.get("session_cookie_path", "/")
            httponly = config.get(
                "cookie_httponly", False
            )  # Default False for development
            secure = config.get(
                "cookie_secure", False
            )  # Default False for HTTP (localhost)
            samesite = config.get("cookie_samesite", "lax")
        else:
            # Development-friendly defaults if no config provided
            cookie_name = "auth_session"
            default_max_age = 7 * 24 * 60 * 60
            path = "/"
            httponly = False
            secure = False  # Allow HTTP (localhost)
            samesite = "lax"

        # Set max_age: 30 days if remember_me, otherwise use default
        max_age = 30 * 24 * 60 * 60 if remember_me else default_max_age

        response.set_cookie(
            key=cookie_name,
            value=session_id,
            max_age=max_age,
            path=path,
            httponly=httponly,
            secure=secure,
            samesite=samesite,
        )

    @staticmethod
    def delete_session_cookie(
        response: Response | JSONResponse, config: Config | None = None
    ) -> None:
        """Delete session cookie from response.

        Args:
        ----
            response: FastAPI response object
            config: Configuration instance for cookie settings (optional)

        """
        if config:
            cookie_name = config.get("auth_session_cookie_name", "auth_session")
            path = config.get("session_cookie_path", "/")
        else:
            cookie_name = "auth_session"
            path = "/"

        response.delete_cookie(key=cookie_name, path=path)

    @staticmethod
    def delete_auth_cookies(response: Response | JSONResponse) -> None:
        """Delete authentication cookies from response.

        Args:
        ----
            response: FastAPI response object

        """
        access_token_key, refresh_token_key = get_token_cookie_names()
        response.delete_cookie(key=access_token_key, path="/")
        response.delete_cookie(key=refresh_token_key, path="/")


__all__ = ["CookieManager"]
