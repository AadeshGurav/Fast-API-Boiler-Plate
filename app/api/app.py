from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.types import Lifespan

if TYPE_CHECKING:
    from app.services.base_service import BaseService
    from app.services.logger import Logger
    from config import Config


class AppFactory:
    """Factory for creating FastAPI application instances."""

    def __init__(
        self: AppFactory,
        app_name: str,
        logger: Logger,
        config: Config,
        debug: bool = False,
        services: dict[str, BaseService] = {},
        life_span: Lifespan | None = None,
    ) -> None:
        self.app_name: str = app_name
        self.config: Config = config
        self.logger: Logger = logger
        self.debug: bool = debug
        self.app: FastAPI | None = None
        self.life_span: Lifespan | None = life_span
        self.services: dict[str, BaseService] = services
        self.logger.info("AppFactory initialized", extra={"service": "AppFactory"})

    def create_app(self: AppFactory, life_span: Lifespan | None = None) -> FastAPI:
        """Create and configure FastAPI app."""
        if life_span:
            self.life_span = life_span

        self.app = FastAPI(
            title=self.app_name,
            debug=self.debug,
            lifespan=self.life_span,
            docs_url="/docs" if self.debug else None,
            redoc_url="/redoc" if self.debug else None,
            version=self.config.get("app_version", "1.0.0"),
            description=self.config.get(
                "app_description", "Production-ready FastAPI application"
            ),
        )

        # store critical services in state
        self.app.state.config = self.config
        self.app.state.logger = self.logger

        # Initialize optional services safely
        self._initialize_services()

        # Setup middleware, logging, static files, templates, and routes
        self.__setup_middleware()
        self.__setup_logging_middleware()
        self.__setup_static_files()
        self.__setup_templates()
        self.__setup_routes()

        self.logger.info("App created", extra={"service": "AppFactory"})
        return self.app

    def _initialize_services(self: AppFactory) -> None:
        """Safely initialize optional services (retry, metrics, tracing, sentry)."""
        try:
            # Resolve dependency_injector providers into concrete instances
            from dependency_injector import providers as _di_providers

            for key, value in self.services.items():
                instance = (
                    value() if isinstance(value, _di_providers.Provider) else value
                )
                setattr(self.app.state, key, instance)
                setattr(self, f"_{key}", instance)
                self.logger.info(
                    f"Set {key} Service in App Factory", extra={"service": "AppFactory"}
                )

            # Instrument tracing if available
            if getattr(self, "_tracing_service", None):
                self.app.state.tracing_service.instrument_app(self.app)

            # Log Sentry ready
            sentry_service = getattr(self, "_sentry_service", None)
            if sentry_service and sentry_service.is_enabled():
                self.logger.info(
                    "Sentry service ready", extra={"service": "AppFactory"}
                )

        except Exception as e:  # noqa: BLE001
            self.logger.warning(
                f"Failed to initialize optional services: {e}",
                extra={"service": "AppFactory"},
            )

    def __get_cors_origins(self: AppFactory) -> list[str]:
        """Get CORS origins from config."""
        default = ["http://localhost", "http://localhost:3000", "http://localhost:8000"]
        config_origins = self.config.get("cors_origins", [])
        origins = list(set(default + config_origins))
        if self.debug:
            origins.extend(["http://localhost:*", "http://127.0.0.1:*"])
        return origins

    def __setup_static_files(self: AppFactory) -> None:
        """Mount static files."""
        static_path = Path(__file__).parent.parent / "static"
        if static_path.exists():
            self.app.mount(
                "/static", StaticFiles(directory=str(static_path)), name="static"
            )
            self.logger.info(
                f"Mounted static files from {static_path}",
                extra={"service": "AppFactory"},
            )
        else:
            self.logger.warning(
                f"Static files directory not found: {static_path}",
                extra={"service": "AppFactory"},
            )

    def __setup_templates(self: AppFactory) -> None:
        """Configure templates."""
        from jinja2 import Environment, FileSystemLoader

        from app.utils.template_filters import safe_user_json

        templates_path = Path(__file__).parent.parent / "templates"
        if templates_path.exists():
            env = Environment(loader=FileSystemLoader(str(templates_path)))
            env.filters["safe_user_json"] = safe_user_json
            self.app.state.templates = Jinja2Templates(env=env)
            
            # Verify filter is registered
            if "safe_user_json" not in env.filters:
                self.logger.error(
                    "Failed to register safe_user_json filter",
                    extra={"service": "AppFactory"},
                )
            else:
                self.logger.info(
                    f"Configured templates from {templates_path} with custom filters",
                    extra={"service": "AppFactory"},
                )
        else:
            self.logger.warning(
                f"Templates directory not found: {templates_path}",
                extra={"service": "AppFactory"},
            )

    def __setup_routes(self: AppFactory) -> None:
        """Include API routers and root endpoint."""
        from app.api.routes.auth import router as auth_router
        from app.api.routes.demo import health_router, sentry_router
        from app.api.routes.files import router as files_router
        from app.api.routes.oauth import router as oauth_router
        from app.api.routes.rbac import router as rbac_router
        from app.api.routes.sessions import router as sessions_router

        # Core routes
        self.app.include_router(health_router, prefix="/api/v1", tags=["health"])
        self.app.include_router(sentry_router, prefix="/api/v1")

        # Authentication and RBAC routes
        self.app.include_router(auth_router, prefix="/api/v1")
        self.app.include_router(oauth_router, prefix="/api/v1")
        self.app.include_router(rbac_router, prefix="/api/v1")
        self.app.include_router(sessions_router, prefix="/api/v1")

        # File management routes
        self.app.include_router(files_router, prefix="/api/v1/files")

        # Demo routes (HTML templates) - Unified demo
        from app.api.routes.demo import (
            demo_router,
            files_play_router,
            files_router,
            library_router,
        )

        self.app.include_router(demo_router)
        self.app.include_router(library_router)
        self.app.include_router(files_router)
        self.app.include_router(files_play_router)

        self.logger.info("Routes configured", extra={"service": "AppFactory"})

        @self.app.get("/")
        async def root() -> dict[str, str]:
            return {
                "message": f"Welcome to {self.app_name}",
                "version": self.config.get("app_version", "1.0.0"),
                "docs": "/docs" if self.debug else "Disabled in production",
                "demo": "Visit /demo/ for comprehensive demo experience",
            }

    def __setup_logging_middleware(self: AppFactory) -> None:
        """Log requests and responses."""

        @self.app.middleware("http")
        async def log_requests(request: Request, call_next: Callable) -> Response:
            start = time.time()
            request_id = getattr(request.state, "request_id", "unknown")
            client_ip = getattr(request.client, "host", "unknown")

            self.logger.info(
                f"Request started: {request.method} {request.url.path}",
                extra={
                    "service": "AppFactory",
                    "request_id": request_id,
                    "client_ip": client_ip,
                },
            )

            response = await call_next(request)
            duration = time.time() - start
            response.headers["X-Process-Time"] = f"{duration:.3f}"

            self.logger.info(
                f"Request completed: {request.method} {request.url.path}",
                extra={
                    "service": "AppFactory",
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "duration": duration,
                },
            )

            # Metrics if available
            metrics = self._metrics_service
            if metrics:
                metrics.track_request(
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=response.status_code,
                    duration=duration,
                )

            return response

    def __setup_middleware(self: AppFactory) -> None:
        """Register middleware in correct order."""
        from app.api.middleware.circuit_breaker import CircuitBreakerMiddleware
        from app.api.middleware.cors import CORSMiddleware
        from app.api.middleware.error_handler import ErrorHandlerMiddleware
        from app.api.middleware.rate_limiter import RateLimiter
        from app.api.middleware.rbac import RBACMiddleware
        from app.api.middleware.security import RequestIDMiddleware, SecurityHeadersMiddleware
        from app.api.middleware.sentry import SentryMiddleware
        from app.api.middleware.serialization import SerializationMiddleware
        from app.api.middleware.session import SessionMiddleware
        from app.api.middleware.template_context import TemplateContextMiddleware
        from app.api.middleware.timeout import TimeoutMiddleware

        origins = self.__get_cors_origins()

        self.app.add_middleware(
            ErrorHandlerMiddleware,
            config=self.config,
            logger=self.logger,
            error_service=self._error_service,
        )

        if self._sentry_service:
            self.app.add_middleware(
                SentryMiddleware,
                config=self.config,
                logger=self.logger,
                sentry_service=self._sentry_service,
                capture_exceptions=True,
                capture_requests=True,
                set_user_context=True,
            )

        self.app.add_middleware(
            CORSMiddleware,
            config=self.config,
            logger=self.logger,
            allow_origins=origins,
        )

        self.app.add_middleware(
            RequestIDMiddleware,
            config=self.config,
            logger=self.logger,
        )

        if self.config.get("enable_security_headers", True):
            self.app.add_middleware(
                SecurityHeadersMiddleware,
                config=self.config,
                logger=self.logger,
            )

        if self.config.get("enable_timeout_middleware", True) and not self.config.get(
            "app_debug", False
        ):
            self.app.add_middleware(
                TimeoutMiddleware, config=self.config, logger=self.logger
            )

        if self.config.get("enable_circuit_breaker", True):
            self.app.add_middleware(
                CircuitBreakerMiddleware,
                config=self.config,
                logger=self.logger,
            )

        if self.config.get("rate_limit_enabled", True):
            self.app.add_middleware(
                RateLimiter,
                config=self.config,
                logger=self.logger,
                redis_client=self._cache_service.redis_client,
            )

        self.app.add_middleware(
            SessionMiddleware,
            config=self.config,
            logger=self.logger,
            data_service=self._data_service,
        )

        self.app.add_middleware(
            SerializationMiddleware, config=self.config, logger=self.logger
        )

        self.app.add_middleware(
            TemplateContextMiddleware, config=self.config, logger=self.logger
        )

        self.app.add_middleware(
            RBACMiddleware,
            config=self.config,
            logger=self.logger,
            rbac_service=self._rbac_service,
            error_service=self._error_service,
        )

        self.logger.info("Middleware stack configured", extra={"service": "AppFactory"})
