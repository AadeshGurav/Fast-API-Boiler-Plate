from __future__ import annotations

from dependency_injector import containers, providers
from fastapi import FastAPI

from app.api.app import AppFactory
from app.core.class_store import ClassStore
from app.services.auth import AuthService
from app.services.cache import CacheService
from app.services.data import DataService
from app.services.database_service import DatabaseService
from app.services.error.error_service import ErrorService
from app.services.file import FileService
from app.services.file.storage.local import LocalStorage
from app.services.logger import Logger
from app.services.metrics import MetricsService
from app.services.oauth import OAuthService
from app.services.password_service import PasswordService
from app.services.rbac import RBACService
from app.services.retry_service import RetryService
from app.services.sentry import SentryService
from app.services.session import SessionService
from app.services.tracing import TracingService
from app.utils.utils import lifespan
from config import Config


class Container(containers.DeclarativeContainer):
    """Main dependency injection container."""

    # Add wiring configuration
    wiring_config = containers.WiringConfiguration(
        modules=[
            "config",
            "app.services.logger",
            "app.services.retry_service",
            "app.services.metrics",
            "app.services.tracing",
            "app.services.sentry",
            "app.services.data",
            "app.services.database_service",
            "app.services.cache",
            "app.services.password_service",
            "app.services.rbac",
            "app.services.oauth",
            "app.services.auth",
            "app.services.session",
            "app.services.error",
            "app.services.file",
            "app.core.class_store",
        ]
    )

    # Configuration provider - using lazy import to avoid circular dependency
    config = providers.Singleton(Config)

    # Logger with direct configuration
    logger: Logger = providers.Singleton(
        Logger,
        config=config,
    )

    # Retry service
    retry_service = providers.Singleton(
        RetryService,
        logger=logger,
        config=config,
    )

    # Metrics service
    metrics_service = providers.Singleton(
        MetricsService,
        logger=logger,
        config=config,
    )

    # Tracing service
    tracing_service = providers.Singleton(
        TracingService,
        logger=logger,
        config=config,
    )

    # Sentry service
    sentry_service = providers.Singleton(
        SentryService,
        logger=logger,
        config=config,
    )

    # Services

    database_service: DatabaseService = providers.Singleton(
        DatabaseService,
        config=config,
        logger=logger
    )

    # Cache service - get from data_service
    cache_service: CacheService = providers.Singleton(CacheService, config=config, logger=logger)

    # Database
    data_service: DataService = providers.Singleton(
        DataService, logger=logger, config=config, database_service=database_service, cache_service=cache_service
    )

    # Password service
    password_service: PasswordService = providers.Singleton(
        PasswordService,
        config=config,
        logger=logger,
    )

    # RBAC service
    rbac_service: RBACService = providers.Singleton(
        RBACService,
        config=config,
        logger=logger,
        data_service=data_service,
        cache_service=cache_service,
    )

    # OAuth service
    oauth_service: OAuthService = providers.Singleton(
        OAuthService,
        config=config,
        logger=logger,
        data_service=data_service,
    )

    # Enhanced Auth service
    auth_service: AuthService = providers.Singleton(
        AuthService,
        logger=logger,
        config=config,
        data_service=data_service,
        password_service=password_service,
        rbac_service=rbac_service,
    )

    session_service: SessionService = providers.Singleton(
        SessionService, config=config, logger=logger, data_service=data_service
    )

    # ErrorService as a core singleton
    error_service: ErrorService = providers.Singleton(
        ErrorService, logger=logger, config=config
    )

    # Storage backend for files
    storage_backend: LocalStorage = providers.Singleton(
        LocalStorage,
        logger=logger,
        config=config,
    )

    # File service
    file_service: FileService = providers.Singleton(
        FileService,
        logger=logger,
        config=config,
        data_service=data_service,
        storage_backend=storage_backend,
    )

    # ClassStore (soft dependencies)
    # Use factory to set container reference after creation
    class_store: ClassStore = providers.Singleton(
        ClassStore, config=config, logger=logger
    )

    # FastAPI application factory
    app_factory: AppFactory = providers.Singleton(
        AppFactory,
        app_name=config.provided.app_title,
        config=config,
        logger=logger,
        debug=config.provided.app_debug,
        life_span=lifespan,
        services={
            "retry_service": retry_service,
            "metrics_service": metrics_service,
            "tracing_service": tracing_service,
            "sentry_service": sentry_service,
            "data_service": data_service,
            "database_service": database_service,
            "cache_service": cache_service,
            "password_service": password_service,
            "rbac_service": rbac_service,
            "oauth_service": oauth_service,
            "auth_service": auth_service,
            "session_service": session_service,
            "error_service": error_service,
            "file_service": file_service,
            "class_store": class_store,
        },
    )

    # FastAPI application instance
    app: FastAPI = providers.Singleton(
        app_factory.provided.create_app.call()
    )

    # TODO: user proper DI injection instead of this
    def init_app(self: Container) -> None:
        """Discover and wire services after container is built."""
        class_store_instance = self.class_store()
        # Set container reference for service access
        class_store_instance._container = self
        class_store_instance.discover_services(
            ["app.services", "app.api", "app.classes"]
        )
