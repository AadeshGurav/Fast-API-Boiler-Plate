from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.types import Lifespan

from app.services.data_service import DataService
from app.services.logger import Logger


class AppFactory:
    """Factory for creating FastAPI application instances."""

    def __init__(
        self: AppFactory,
        app_name: str,
        logger: Logger,
        config: dict,
        data_service: DataService,
        *,  # force keyword-only
        debug: bool = False,
        life_span: Lifespan | None = None,
    ) -> None:
        self.app_name: str = app_name
        self.config: dict = config
        self.logger: Logger = logger
        self.data_service: DataService = data_service
        self.debug: bool = debug
        self.app: FastAPI | None = None
        self.life_span: Lifespan | None = life_span

        # Track app start time for metrics
        self.data_service._start_time = time.time()
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
        self.app.state.data_service = self.data_service

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
            from app.core.container import Container

            container = Container()
            self.app.state.retry_service = container.retry_service()
            self.app.state.metrics_service = container.metrics_service()
            self.app.state.tracing_service = container.tracing_service()
            self.app.state.sentry_service = container.sentry_service()
            self.app.state.error_service = container.error_service()

            # Instrument tracing if available
            if self.app.state.tracing_service:
                self.app.state.tracing_service.instrument_app(self.app)

            # Log Sentry ready
            sentry_service = getattr(self.app.state, "sentry_service", None)
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
        templates_path = Path(__file__).parent.parent / "templates"
        if templates_path.exists():
            self.app.state.templates = Jinja2Templates(directory=str(templates_path))
            self.logger.info(
                f"Configured templates from {templates_path}",
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

        # Demo routes (HTML templates) - Unified demo
        from app.api.routes.demo import demo_router

        self.app.include_router(demo_router)

        self.logger.info("Routes configured", extra={"service": "AppFactory"})

        @self.app.get("/")
        async def root(self: AppFactory) -> dict[str, str]:
            return {
                "message": f"Welcome to {self.app_name}",
                "version": self.config.get("app_version", "1.0.0"),
                "docs": "/docs" if self.debug else "Disabled in production",
                "demo": "Visit /demo/ for comprehensive demo experience",
            }

    def __setup_logging_middleware(self: AppFactory) -> None:
        """Log requests and responses."""

        @self.app.middleware("http")
        async def log_requests(
            self: AppFactory, request: Request, call_next: Callable
        ) -> Response:
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
            metrics = getattr(self.app.state, "metrics_service", None)
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
        from app.api.middleware.security import (
            RequestIDMiddleware,
            SecurityHeadersMiddleware,
        )
        from app.api.middleware.sentry import SentryMiddleware
        from app.api.middleware.serialization import SerializationMiddleware
        from app.api.middleware.session import SessionMiddleware
        from app.api.middleware.template_context import TemplateContextMiddleware
        from app.api.middleware.timeout import TimeoutMiddleware

        origins = self.__get_cors_origins()

        self.app.add_middleware(
            ErrorHandlerMiddleware, config=self.config, logger=self.logger
        )

        if getattr(self.app.state, "sentry_service", None):
            self.app.add_middleware(
                SentryMiddleware,
                sentry_service=self.app.state.sentry_service,
                capture_exceptions=True,
                capture_requests=True,
                set_user_context=True,
                config=self.config,
                logger=self.logger,
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
                redis_client=self.data_service.cache_service.redis_client,
                config=self.config,
                logger=self.logger,
            )

        self.app.add_middleware(
            SessionMiddleware,
            config=self.config,
            logger=self.logger,
            cache_service=self.data_service.cache_service,
            database_service=self.data_service.database_service,
        )

        self.app.add_middleware(
            SerializationMiddleware, config=self.config, logger=self.logger
        )

        self.app.add_middleware(
            TemplateContextMiddleware, config=self.config, logger=self.logger
        )

        self.app.add_middleware(RBACMiddleware, config=self.config, logger=self.logger)

        self.logger.info("Middleware stack configured", extra={"service": "AppFactory"})
