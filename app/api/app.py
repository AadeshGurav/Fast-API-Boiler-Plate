from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI, Request, Response

if TYPE_CHECKING:
    from starlette.types import Lifespan

    from app.services.logger import Logger
    from app.services.registry import Services
    from config import Config


class AppFactory:
    """Builds the FastAPI application from a set of services."""

    def __init__(self, services: Services, life_span: Lifespan | None = None) -> None:
        self.services = services
        self.config: Config = services.config
        self.logger: Logger = services.logger
        self.debug: bool = bool(self.config["app_debug"])
        self.app_name: str = self.config["app_title"]
        self.life_span = life_span
        self.app: FastAPI | None = None

    def create_app(self) -> FastAPI:
        """Create and configure the FastAPI app."""
        self.app = FastAPI(
            title=self.app_name,
            debug=self.debug,
            lifespan=self.life_span,
            docs_url="/docs" if self.debug else None,
            redoc_url="/redoc" if self.debug else None,
            version=self.config["app_version"],
            description=self.config["app_description"],
            # operationId = the route function's name, so generated clients get stable,
            # readable method names (``login_user`` rather than ``login_user_api_v1_auth_...``).
            generate_unique_id_function=lambda route: route.name,
        )
        self.app.state.services = self.services

        if self.services.tracing_service is not None:
            self.services.tracing_service.instrument_app(self.app)

        self.__setup_exception_handlers()
        self.__setup_middleware()
        self.__setup_routes()

        self.logger.info("App created", extra={"service": "AppFactory"})
        return self.app

    def __get_cors_settings(self: AppFactory) -> dict:
        """Starlette CORSMiddleware settings from config.

        Origins must be exact (credentials are on, so ``*`` is invalid). Debug mode
        additionally accepts any localhost port.
        """
        origins = sorted(
            {
                *self.config["cors_origins"],
                # Local frontends are convenient in development and a credentialed foothold
                # in production, so they are only trusted in debug mode.
                *(
                    ["http://localhost", "http://localhost:3000", "http://localhost:8000"]
                    if self.debug
                    else []
                ),
            }
        )
        if "*" in origins:
            raise ValueError(
                "cors_origins must list exact origins; '*' cannot be combined with credentials."
            )
        return {
            "allow_origins": origins,
            "allow_origin_regex": (
                r"https?://(localhost|127\.0\.0\.1)(:\d+)?" if self.debug else None
            ),
            "allow_credentials": self.config["cors_allow_credentials"],
            "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": [
                "Authorization",
                "Content-Type",
                "X-Requested-With",
                "Idempotency-Key",
            ],
            "expose_headers": self.config["cors_expose_headers"],
            "max_age": 600,
        }

    def __setup_routes(self: AppFactory) -> None:
        """Include API routers and root endpoint."""
        from app.api.routes.auth import router as auth_router
        from app.api.routes.files import router as files_router
        from app.api.routes.health import router as health_router
        from app.api.routes.oauth import router as oauth_router
        from app.api.routes.rbac import router as rbac_router
        from app.api.routes.sessions import router as sessions_router
        from app.api.routes.users import router as users_router

        # Core routes
        self.app.include_router(health_router, prefix="/api/v1", tags=["health"])

        # Authentication and RBAC routes
        self.app.include_router(auth_router, prefix="/api/v1")
        self.app.include_router(oauth_router, prefix="/api/v1")
        self.app.include_router(rbac_router, prefix="/api/v1")
        self.app.include_router(sessions_router, prefix="/api/v1")
        self.app.include_router(users_router, prefix="/api/v1")

        # File management routes
        self.app.include_router(files_router, prefix="/api/v1/files")

        self.logger.info("Routes configured", extra={"service": "AppFactory"})

        @self.app.get("/", include_in_schema=False)
        async def root() -> dict[str, str]:
            return {
                "message": f"Welcome to {self.app_name}",
                "version": self.config["app_version"],
                "docs": "/docs" if self.debug else "Disabled in production",
            }

    def __setup_exception_handlers(self: AppFactory) -> None:
        """Answer every HTTP and validation error with an RFC 9457 problem document."""
        from fastapi.exceptions import RequestValidationError
        from starlette.exceptions import HTTPException as StarletteHTTPException

        error_service = self.services.error_service

        @self.app.exception_handler(StarletteHTTPException)
        async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> Response:
            return error_service.http_response(exc, headers=exc.headers, instance=request.url.path)

        @self.app.exception_handler(RequestValidationError)
        async def validation_exception_handler(
            request: Request, exc: RequestValidationError
        ) -> Response:
            return error_service.http_response(exc, instance=request.url.path)

    def __setup_middleware(self: AppFactory) -> None:
        """Register middleware.

        Starlette runs the *last* middleware added first, so the list below goes from
        innermost to outermost. Resulting request flow::

            request id -> security headers -> body limit -> CSRF origin check -> CORS -> error handler ->
            timeout -> rate limiter -> session cookies ->
            RBAC (authentication + authorization) -> route

        CORS wraps everything that can reject a request (rate limit, 401, 403), so
        browsers see those responses instead of an opaque CORS failure; the error
        handler wraps the rest so no exception escapes without a problem response.
        """
        from starlette.middleware.cors import CORSMiddleware

        from app.api.middleware.access_log import AccessLogMiddleware
        from app.api.middleware.body_limit import BodySizeLimitMiddleware
        from app.api.middleware.csrf import CSRFOriginMiddleware
        from app.api.middleware.error_handler import ErrorHandlerMiddleware
        from app.api.middleware.idempotency import IdempotencyMiddleware
        from app.api.middleware.rate_limiter import RateLimiter
        from app.api.middleware.rbac import RBACMiddleware
        from app.api.middleware.security import (
            RequestIDMiddleware,
            SecurityHeadersMiddleware,
        )
        from app.api.middleware.session import SessionMiddleware
        from app.api.middleware.timeout import TimeoutMiddleware

        common = {"config": self.config, "logger": self.logger}
        add = self.app.add_middleware

        add(
            RBACMiddleware,
            **common,
            rbac_service=self.services.rbac_service,
            error_service=self.services.error_service,
        )
        add(SessionMiddleware, **common)
        add(IdempotencyMiddleware, **common, cache=self.services.cache_service)

        if self.config["rate_limit_enabled"]:
            add(
                RateLimiter,
                **common,
                cache=self.services.cache_service,
            )
        if self.config["timeout_enabled"] and not self.debug:
            add(TimeoutMiddleware, **common)

        add(AccessLogMiddleware, **common, metrics=self.services.metrics_service)
        add(
            ErrorHandlerMiddleware,
            **common,
            error_service=self.services.error_service,
        )
        add(CORSMiddleware, **self.__get_cors_settings())
        if self.config["csrf_origin_check"]:
            add(CSRFOriginMiddleware, allowed_origins=self.__get_cors_settings()["allow_origins"])
        add(
            BodySizeLimitMiddleware,
            max_body_bytes=self.config["max_request_body_bytes"],
            idle_timeout=self.config["request_body_idle_timeout_seconds"],
        )
        if self.config["enable_security_headers"]:
            add(SecurityHeadersMiddleware, **common)
        add(
            RequestIDMiddleware,
            **common,
            tracing_service=self.services.tracing_service,
        )

        self.logger.info("Middleware stack configured", extra={"service": "AppFactory"})


def create_app(config: Config | None = None) -> FastAPI:
    """Application factory: ``uvicorn app.api.app:create_app --factory``."""
    from app.services.registry import build_services
    from app.utils.utils import lifespan
    from config import Config as ConfigClass

    config = config or ConfigClass()
    config.ensure_secret("jwt_secret")  # any entry point must have a signing secret
    return AppFactory(build_services(config), life_span=lifespan).create_app()
