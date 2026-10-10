"""Security and request tracing middleware for FastAPI."""

from __future__ import annotations

import re
import uuid
from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.types import Message, Receive, Send

from app.services.logger import create_log_context, set_request_id

from .base import BaseMiddleware, set_headers

if TYPE_CHECKING:
    from app.services.tracing import TracingService

REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9._-]{8,64}")


class SecurityHeadersMiddleware(BaseMiddleware):
    """Middleware to add security headers to all responses.

    Implements recommended security headers (OWASP):
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Strict-Transport-Security
    - Content-Security-Policy
    - Referrer-Policy
    - Permissions-Policy
    """

    def initialize(
        self: SecurityHeadersMiddleware,
        **kwargs,
    ) -> None:
        """Initialize security headers middleware.

        Args:
        ----
            kwargs: Additional keyword arguments

        """
        # HSTS
        self.enable_hsts = not self.config["app_debug"] or self.config["enable_hsts"]
        self.hsts_max_age = self.config["hsts_max_age"]
        self.hsts_include_subdomains = self.config["hsts_include_subdomains"]
        self.hsts_preload = self.config["hsts_preload"]

        # Frame options
        self.frame_options = self.config["frame_options"]

        # Other headers
        self.content_type_nosniff = self.config["content_type_nosniff"]
        self.xss_protection = self.config["xss_protection"]
        self.referrer_policy = self.config["referrer_policy"]

        # Content Security Policy
        # Strict CSP everywhere except debug, where Swagger UI and the demo pages
        # need inline scripts and CDN assets.
        self.csp_enabled = self.config["csp_enabled"]
        self.csp_directives = self.config["csp_directives"] or self._default_csp_directives()
        self.generate_nonce = any("nonce-" in str(v) for v in self.csp_directives.values())

        # Permissions Policy
        self.permissions_policy_enabled = self.config["permissions_policy_enabled"]
        self.permissions_policy = (
            self.config["permissions_policy"] or self._default_permissions_policy()
        )

        self.logger.info(
            "SecurityHeadersMiddleware initialized",
            extra=create_log_context(middleware="SecurityHeadersMiddleware"),
        )

    def _default_csp_directives(self: SecurityHeadersMiddleware) -> dict:
        """Default Content Security Policy directives.

        Returns
        -------
            Default Content Security Policy directives

        """
        return {
            "default-src": ["'self'"],
            "script-src": ["'self'"],
            "style-src": ["'self'", "'unsafe-inline'"],
            "img-src": ["'self'", "data:", "https:"],
            "font-src": ["'self'"],
            "connect-src": ["'self'"],
            "media-src": ["'self'"],
            "object-src": ["'none'"],
            "base-uri": ["'self'"],
            "form-action": ["'self'"],
            "frame-ancestors": ["'none'"],
            "upgrade-insecure-requests": [],
        }

    def _default_permissions_policy(self: SecurityHeadersMiddleware) -> dict:
        """Default Permissions Policy.

        Returns
        -------
            Default Permissions Policy

        """
        return {
            "accelerometer": [],
            "camera": [],
            "geolocation": [],
            "gyroscope": [],
            "magnetometer": [],
            "microphone": [],
            "payment": [],
            "usb": [],
        }

    def _build_csp_header(self: SecurityHeadersMiddleware, nonce: str | None = None) -> str:
        """Build Content Security Policy header.

        Args:
        ----
            nonce: Nonce

        Returns:
        -------
            Content Security Policy header

        """
        directives = []
        for directive, values in self.csp_directives.items():
            if not values:
                directives.append(directive)
            else:
                if nonce:
                    values = [v.replace("nonce-", f"nonce-{nonce}") for v in values]
                directives.append(f"{directive} {' '.join(values)}")
        return "; ".join(directives)

    def _build_permissions_policy(self: SecurityHeadersMiddleware) -> str:
        """Build Permissions Policy header.

        Returns
        -------
            Permissions Policy header

        """
        if not self.permissions_policy:
            return ""

        policies = []
        for feature, allowlist in self.permissions_policy.items():
            policies.append(f"{feature}=({' '.join(allowlist)})" if allowlist else f"{feature}=()")
        return ", ".join(policies)

    def _build_hsts_header(self: SecurityHeadersMiddleware) -> str:
        """Build HSTS header.

        Returns
        -------
            HSTS header

        """
        directives = [f"max-age={self.hsts_max_age}"]
        if self.hsts_include_subdomains:
            directives.append("includeSubDomains")
        if self.hsts_preload:
            directives.append("preload")
        return "; ".join(directives)

    async def handle(self, request: Request, receive: Receive, send: Send) -> None:
        """Add the security headers to the response as it starts."""
        nonce = uuid.uuid4().hex if self.generate_nonce else None
        if nonce:
            request.state.csp_nonce = nonce

        def add_headers(message: Message) -> None:
            values: dict[str, str] = {}
            if self.content_type_nosniff:
                values["X-Content-Type-Options"] = "nosniff"
            if self.frame_options:
                values["X-Frame-Options"] = self.frame_options
            if self.xss_protection:
                # The legacy XSS auditor created vulnerabilities of its own; "0" disables
                # it and CSP is the real defence.
                values["X-XSS-Protection"] = "0"
            if self.enable_hsts and request.url.scheme == "https":
                values["Strict-Transport-Security"] = self._build_hsts_header()
            if self.csp_enabled:
                values["Content-Security-Policy"] = self._build_csp_header(nonce)
            if self.referrer_policy:
                values["Referrer-Policy"] = self.referrer_policy
            if self.permissions_policy_enabled:
                values["Permissions-Policy"] = self._build_permissions_policy()
            request_id = getattr(request.state, "request_id", None)
            if request_id:
                values["X-Request-ID"] = request_id
            set_headers(message, values, remove=("server",))

        await self.forward(request, receive, send, on_start=add_headers)


class RequestIDMiddleware(BaseMiddleware):
    """Middleware to generate and propagate request IDs for tracing."""

    def initialize(self: RequestIDMiddleware, **kwargs) -> None:
        """Initialize request ID middleware.

        Args:
        ----
            kwargs: Additional keyword arguments

        """
        self.header_name = self.config["request_id_header"]
        self.tracing_service: TracingService = kwargs.get("tracing_service")
        self.logger.info(
            "RequestIDMiddleware initialized",
            extra=create_log_context(middleware="RequestIDMiddleware"),
        )

    async def handle(self, request: Request, receive: Receive, send: Send) -> None:
        """Assign a request id, expose it to logs and echo it on the response."""
        # Accept a caller's id for cross-service tracing, but only if it is harmless:
        # anything else could forge log lines or smuggle characters into headers.
        supplied = request.headers.get(self.header_name, "")
        request_id = supplied if REQUEST_ID_PATTERN.fullmatch(supplied) else str(uuid.uuid4())
        request.state.request_id = request_id

        trace_id = None
        if self.config["log_enable_trace_correlation"] and self.tracing_service is not None:
            trace_id = self.tracing_service.get_trace_id()

        set_request_id(f"{request_id}|trace:{trace_id}" if trace_id else request_id)
        try:
            await self.forward(
                request,
                receive,
                send,
                on_start=lambda message: set_headers(message, {self.header_name: request_id}),
            )
        finally:
            set_request_id(None)
