"""Centralized cookie management for authentication tokens."""

from __future__ import annotations

from fastapi import Response
from fastapi.responses import JSONResponse

from app.models.auth import TokenPair
from app.utils.permissions import get_token_cookie_names


class CookieManager:
    """Centralized manager for authentication cookie operations."""

    @staticmethod
    def set_auth_cookies(
        response: Response | JSONResponse,
        token_pair: TokenPair,
    ) -> None:
        """Set authentication cookies from a TokenPair.

        Args:
        ----
            response: FastAPI response object
            token_pair: TokenPair containing access and refresh tokens

        """
        access_token_key, refresh_token_key = get_token_cookie_names()

        if token_pair.access_token:
            response.set_cookie(
                key=access_token_key,
                value=token_pair.access_token,
                max_age=token_pair.expires_in,
                httponly=False,  # Allow JavaScript access for localStorage sync
                samesite="lax",
                secure=False,  # Set to True in production with HTTPS
                path="/",
            )

        if token_pair.refresh_token:
            response.set_cookie(
                key=refresh_token_key,
                value=token_pair.refresh_token,
                max_age=7 * 24 * 60 * 60,  # 7 days
                httponly=False,  # Allow JavaScript access for localStorage sync
                samesite="lax",
                secure=False,  # Set to True in production with HTTPS
                path="/",
            )

    @staticmethod
    def set_token_cookies(
        response: Response | JSONResponse,
        access_token: str,
        refresh_token: str,
        expires_in: int,
    ) -> None:
        """Set authentication cookies from individual tokens.

        Args:
        ----
            response: FastAPI response object
            access_token: JWT access token
            refresh_token: JWT refresh token
            expires_in: Access token expiration in seconds

        """
        token_pair = TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )
        CookieManager.set_auth_cookies(response, token_pair)

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
