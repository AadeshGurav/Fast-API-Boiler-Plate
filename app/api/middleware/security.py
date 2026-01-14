"""Security and request tracing middleware for FastAPI."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import Request, Response

from app.services.logger import create_log_context, set_request_id
from app.services.tracing import TracingService

from .base import BaseMiddleware


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
        self.enable_hsts = not self.config.get("app_debug", False) or self.config.get(
            "enable_hsts", True
        )
        self.hsts_max_age = self.config.get("hsts_max_age", 31536000)
        self.hsts_include_subdomains = self.config.get("hsts_include_subdomains", True)
        self.hsts_preload = self.config.get("hsts_preload", False)

        # Frame options
        self.frame_options = self.config.get("frame_options", "DENY")

        # Other headers
        self.content_type_nosniff = self.config.get("content_type_nosniff", True)
        self.xss_protection = self.config.get("xss_protection", True)
        self.referrer_policy = self.config.get(
            "referrer_policy", "strict-origin-when-cross-origin"
        )

        # Content Security Policy
        self.csp_enabled = self.config.get("csp_enabled", True)
        self.csp_directives = (
            self.config.get("csp_directives") or self._default_csp_directives()
        )
        self.generate_nonce = any(
            "nonce-" in str(v) for v in self.csp_directives.values()
        )

        # Permissions Policy
        self.permissions_policy_enabled = self.config.get(
            "permissions_policy_enabled", True
        )
        self.permissions_policy = (
            self.config.get("permissions_policy") or self._default_permissions_policy()
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
            "script-src": ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
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

    def _build_csp_header(
        self: SecurityHeadersMiddleware, nonce: str | None = None
    ) -> str:
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
            policies.append(
                f"{feature}=({' '.join(allowlist)})" if allowlist else f"{feature}=()"
            )
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

    async def process_request(
        self: SecurityHeadersMiddleware, request: Request, call_next: Callable
    ) -> Response:
        """Process request and add security headers.

        Args:
        ----
            request: Request
            call_next: Next callable

        Returns:
        -------
            Response

        """
        nonce = uuid.uuid4().hex if self.generate_nonce else None
        if nonce:
            request.state.csp_nonce = nonce

        response = await call_next(request)

        if self.content_type_nosniff:
            response.headers["X-Content-Type-Options"] = "nosniff"
        if self.frame_options:
            response.headers["X-Frame-Options"] = self.frame_options
        if self.xss_protection:
            response.headers["X-XSS-Protection"] = "1; mode=block"
        if self.enable_hsts and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = self._build_hsts_header()
        if self.csp_enabled:
            response.headers["Content-Security-Policy"] = self._build_csp_header(nonce)
        if self.referrer_policy:
            response.headers["Referrer-Policy"] = self.referrer_policy
        if self.permissions_policy_enabled:
            response.headers["Permissions-Policy"] = self._build_permissions_policy()

        if "Server" in response.headers:
            del response.headers["Server"]

        request_id = getattr(request.state, "request_id", None)
        if request_id:
            response.headers["X-Request-ID"] = request_id

        self.logger.debug(
            "Security headers added to response",
            extra=create_log_context(middleware="SecurityHeadersMiddleware"),
        )

        return response


class RequestIDMiddleware(BaseMiddleware):
    """Middleware to generate and propagate request IDs for tracing."""

    def initialize(self: RequestIDMiddleware, **kwargs) -> None:
        """Initialize request ID middleware.

        Args:
        ----
            kwargs: Additional keyword arguments

        """
        self.header_name = self.config.get("request_id_header", "X-Request-ID")
        self.tracing_service: TracingService = kwargs.get("tracing_service")
        self.logger.info(
            "RequestIDMiddleware initialized",
            extra=create_log_context(middleware="RequestIDMiddleware"),
        )

    async def process_request(
        self: RequestIDMiddleware, request: Request, call_next: Callable
    ) -> Response:
        """Process request and generate request ID.

        Args:
        ----
            request: Request
            call_next: Next callable

        Returns:
        -------
            Response

        """
        request_id = request.headers.get(self.header_name) or str(uuid.uuid4())
        request.state.request_id = request_id

        # Check if trace correlation is enabled
        enable_trace = self.config.get("log_enable_trace_correlation", True)

        if enable_trace:
            # Get trace ID if tracing is active
            trace_id = self.tracing_service.get_trace_id()

            # Combine request ID and trace ID
            if trace_id:
                log_id = f"{request_id}|trace:{trace_id}"
            else:
                log_id = request_id
        else:
            log_id = request_id

        # Propagate request ID to logger via contextvar
        set_request_id(log_id)

        try:
            response = await call_next(request)
            response.headers[self.header_name] = request_id
            self.logger.debug(
                "Request context set",
                extra=create_log_context(
                    middleware="RequestIDMiddleware",
                    request_id=request_id,
                    trace_id=trace_id if enable_trace and trace_id else None,
                ),
            )
            return response
        finally:
            # Clear request ID after request completes
            set_request_id(None)
