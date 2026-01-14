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

    config = providers.Singleton(Config)

    logger: Logger = providers.Singleton(
        Logger,
        config=config,
    )

    database_service: DatabaseService = providers.Singleton(
        DatabaseService,
        config=config,
        logger=logger
    )

    cache_service: CacheService = providers.Singleton(CacheService, config=config, logger=logger)

    data_service: DataService = providers.Singleton(
        DataService, logger=logger, config=config, database_service=database_service, cache_service=cache_service
    )

    password_service: PasswordService = providers.Singleton(
        PasswordService,
        config=config,
        logger=logger,
    )

    rbac_service: RBACService = providers.Singleton(
        RBACService,
        config=config,
        logger=logger,
        data_service=data_service,
        cache_service=cache_service,
    )

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

    error_service: ErrorService = providers.Singleton(
        ErrorService, logger=logger, config=config
    )

    storage_backend: LocalStorage = providers.Singleton(
        LocalStorage,
        logger=logger,
        config=config,
    )

    file_service: FileService = providers.Singleton(
        FileService,
        logger=logger,
        config=config,
        data_service=data_service,
        storage_backend=storage_backend,
    )

    @staticmethod
    def _create_retry_service(cfg: Config, log: Logger) -> RetryService | None:
        """Create retry service if enabled in config."""
        if cfg.get("retry_service"):
            log.info("Retry service: Enabled", extra={"service": "Container"})
            return RetryService(logger=log, config=cfg)
        log.info("Retry service: Disabled", extra={"service": "Container"})
        return None

    @staticmethod
    def _create_metrics_service(cfg: Config, log: Logger) -> MetricsService | None:
        """Create metrics service if enabled in config."""
        if cfg.get("metrics_service"):
            log.info("Metrics service: Enabled", extra={"service": "Container"})
            return MetricsService(logger=log, config=cfg)
        log.info("Metrics service: Disabled", extra={"service": "Container"})
        return None

    @staticmethod
    def _create_tracing_service(cfg: Config, log: Logger) -> TracingService | None:
        """Create tracing service if enabled in config."""
        if cfg.get("tracing_service"):
            log.info("Tracing service: Enabled", extra={"service": "Container"})
            return TracingService(logger=log, config=cfg)
        log.info("Tracing service: Disabled", extra={"service": "Container"})
        return None

    @staticmethod
    def _create_sentry_service(cfg: Config, log: Logger) -> SentryService | None:
        """Create sentry service if enabled in config."""
        if cfg.get("sentry_service"):
            log.info("Sentry service: Enabled", extra={"service": "Container"})
            return SentryService(logger=log, config=cfg)
        log.info("Sentry service: Disabled", extra={"service": "Container"})
        return None

    @staticmethod
    def _create_oauth_service(
        cfg: Config, log: Logger, data_svc: DataService
    ) -> OAuthService | None:
        """Create oauth service if enabled in config."""
        if cfg.get("oauth_service"):
            log.info("OAuth service: Enabled", extra={"service": "Container"})
            return OAuthService(config=cfg, logger=log, data_service=data_svc)
        log.info("OAuth service: Disabled", extra={"service": "Container"})
        return None

    retry_service = providers.Factory(
        _create_retry_service,
        cfg=config,
        log=logger,
    )

    metrics_service = providers.Factory(
        _create_metrics_service,
        cfg=config,
        log=logger,
    )

    tracing_service = providers.Factory(
        _create_tracing_service,
        cfg=config,
        log=logger,
    )

    sentry_service = providers.Factory(
        _create_sentry_service,
        cfg=config,
        log=logger,
    )

    oauth_service = providers.Factory(
        _create_oauth_service,
        cfg=config,
        log=logger,
        data_svc=data_service,
    )

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
