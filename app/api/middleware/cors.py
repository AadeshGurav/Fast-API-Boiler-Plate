"""CORS and authentication middleware for FastAPI.

Handles cross-origin requests and token-based user authentication.
"""

from __future__ import annotations

from collections.abc import Callable

import jwt
from fastapi import Request
from starlette.responses import JSONResponse, Response

from app.core.container import Container

from .base import BaseMiddleware


class CORSMiddleware(BaseMiddleware):
    """CORS Middleware with optional token-based authentication."""

    def initialize(self: CORSMiddleware, allow_origins: list[str], **kwargs) -> None:
        """Initialize middleware configuration.

        Args:
        ----
            config: A dictionary containing middleware settings.
            allow_origins: The list of allowed origins.
            kwargs: Additional keyword arguments.

        """
        self.allow_origins: list[str] = allow_origins
        self.allow_credentials: bool = self.config.get("cors_allow_credentials", True)
        self.allow_methods: list[str] = self.config.get("cors_allow_methods", ["*"])
        self.allow_headers: list[str] = self.config.get("cors_allow_headers", ["*"])
        self.expose_headers: list[str] = self.config.get("cors_expose_headers", ["*"])
        self.public_paths: list[str] = self.config.get(
            "public_routes", self.public_paths or []
        )

        self.logger.info(
            "CORS Middleware initialized",
            extra={
                "allow_credentials": self.allow_credentials,
                "allow_origins": self.allow_origins,
                "allow_methods": self.allow_methods,
                "allow_headers": self.allow_headers,
                "expose_headers": self.expose_headers,
                "public_routes": self.public_paths,
                "middleware": "CORSMiddleware",
            },
        )

    async def process_request(
        self: CORSMiddleware, request: Request, call_next: Callable
    ) -> Response:
        """Process the request with CORS and optional authentication.

        Args:
        ----
            request: The incoming HTTP request.
            call_next: The next callable in the middleware chain.

        Returns:
        -------
            The HTTP response.

        """
        path = request.url.path
        is_public = self.is_public_path(path)
        self.logger.debug(
            f"Processing request for path '{path}', public: {is_public}",
            extra={"middleware": "CORSMiddleware"},
        )

        if not is_public:
            from app.utils.permissions import get_token_cookie_names

            access_token_key, _ = get_token_cookie_names()
            access_token = request.cookies.get(access_token_key)
            if not access_token:
                self.logger.warning(
                    f"Missing access token for protected route '{path}'",
                    extra={"middleware": "CORSMiddleware"},
                )
                return await self._handle_error(request, 401, "Authentication required")

            try:
                auth_service = Container.auth_service()
                user_data = auth_service.decode_token(access_token)
                self.logger.info(
                    f"Access token decoded successfully for path '{path}'",
                    extra={
                        "user": user_data.get("sub"),
                        "role": user_data.get("role"),
                        "middleware": "CORSMiddleware",
                    },
                )

                # Update template context if available
                if hasattr(request.state, "template_context"):
                    request.state.template_context.update(
                        {
                            "user_authenticated": True,
                            "username": user_data.get("sub"),
                            "user_role": user_data.get("role"),
                        }
                    )

            except jwt.ExpiredSignatureError:
                self.logger.warning(
                    f"Expired token for path '{path}'",
                    extra={"middleware": "CORSMiddleware"},
                )
                return await self._handle_error(request, 401, "Token expired")
            except Exception as e:  # noqa: BLE001
                self.logger.error(
                    f"Authentication failed for path '{path}': {e}",
                    extra={"middleware": "CORSMiddleware"},
                )
                return await self._handle_error(
                    request, 401, f"Authentication failed: {e}"
                )

        response = await call_next(request)
        self._add_cors_headers(response)
        self.logger.debug(
            f"Request processed successfully for path '{path}'",
            extra={"middleware": "CORSMiddleware"},
        )
        return response

    async def _handle_error(
        self: CORSMiddleware, request: Request, status_code: int, message: str
    ) -> Response:
        """Handle error responses, rendering template if available.

        Args:
        ----
            request: The incoming HTTP request.
            status_code: The HTTP status code.
            message: The error message.

        Returns:
        -------
            The HTTP response.

        """
        self.logger.debug(
            f"Handling error {status_code}: {message}",
            extra={"middleware": "CORSMiddleware"},
        )

        accept_header = request.headers.get("accept", "")
        context = getattr(request.state, "template_context", {})

        # Attempt template rendering if HTML is accepted
        if "text/html" in accept_header and hasattr(request.app, "templates"):
            template_name = f"errors/{status_code}.html"
            try:
                self.logger.debug(
                    f"Rendering template '{template_name}'",
                    extra={"middleware": "CORSMiddleware"},
                )
                return request.app.templates.TemplateResponse(
                    template_name,
                    {"request": request, "detail": message, **context},
                    status_code=status_code,
                )
            except Exception as e:  # noqa: BLE001
                self.logger.error(
                    f"Template rendering failed: {e}, falling back to JSON response",
                    extra={"middleware": "CORSMiddleware"},
                )

        # Default JSON response
        self.logger.debug(
            "Returning JSON error response", extra={"middleware": "CORSMiddleware"}
        )
        return JSONResponse(status_code=status_code, content={"detail": message})

    def _add_cors_headers(self: CORSMiddleware, response: Response) -> None:
        """Add CORS headers to the response.

        Args:
        ----
            response: The HTTP response.

        """
        response.headers["Access-Control-Allow-Credentials"] = str(
            self.allow_credentials
        ).lower()
        response.headers["Access-Control-Allow-Origin"] = ", ".join(self.allow_origins)
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
        response.headers["Access-Control-Expose-Headers"] = ", ".join(
            self.expose_headers
        )
        self.logger.debug(
            "CORS headers applied to response", extra={"middleware": "CORSMiddleware"}
        )
