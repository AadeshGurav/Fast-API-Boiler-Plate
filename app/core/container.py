from __future__ import annotations
from dependency_injector import containers, providers
from fastapi import FastAPI

from app.api.app import AppFactory
from app.core.class_store import ClassStore
from app.database.repositories import (
    OAuthRepository,
    RBACRepository,
    SessionRepository,
    UserRepository,
)
from app.services.auth import AuthService
from app.services.cache import CacheService
from app.services.data_service import DataService
from app.services.database_service import DatabaseService
from app.services.error.error_service import ErrorService
from app.services.logger import Logger
from app.services.metrics import MetricsService
from app.services.oauth import OAuthService
from app.services.password_service import PasswordService
from app.services.rbac import RBACService
from app.services.retry_service import RetryService
from app.services.sentry import SentryService
from app.services.session import SessionService
from app.services.tracing import TracingService
from config import Config


class Container(containers.DeclarativeContainer):
    """Main dependency injection container."""

    # Add wiring configuration
    wiring_config = containers.WiringConfiguration(
        modules=[
            "config",
            "app.services.logger",
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
    data_service: DataService = providers.Singleton(
        DataService, logger=logger, config=config
    )

    # Database service - get from data_service
    database_service: DatabaseService = providers.Singleton(
        lambda data_service: data_service.database_service,
        data_service=data_service,
    )

    # Cache service - get from data_service
    cache_service: CacheService = providers.Singleton(
        lambda data_service: data_service.cache_service,
        data_service=data_service,
    )

    # Repositories
    user_repository: UserRepository = providers.Singleton(
        UserRepository,
        database_service=database_service,
        logger=logger,
    )

    session_repository: SessionRepository = providers.Singleton(
        SessionRepository,
        database_service=database_service,
        cache_service=cache_service,
        logger=logger,
    )

    rbac_repository: RBACRepository = providers.Singleton(
        RBACRepository,
        database_service=database_service,
        cache_service=cache_service,
        logger=logger,
    )

    oauth_repository: OAuthRepository = providers.Singleton(
        OAuthRepository,
        database_service=database_service,
        logger=logger,
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
        rbac_repository=rbac_repository,
        cache_service=cache_service,
    )

    # OAuth service
    oauth_service: OAuthService = providers.Singleton(
        OAuthService,
        config=config,
        logger=logger,
        oauth_repository=oauth_repository,
        user_repository=user_repository,
    )

    # Enhanced Auth service
    auth_service: AuthService = providers.Singleton(
        AuthService,
        logger=logger,
        config=config,
        session_repository=session_repository,
        user_repository=user_repository,
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

    # ClassStore (soft dependencies)
    class_store: ClassStore = providers.Singleton(
        ClassStore, config=config, logger=logger
    )

    # FastAPI application factory
    app_factory: AppFactory = providers.Singleton(
        AppFactory,
        app_name=config.provided.app_title,
        config=config,
        logger=logger,
        data_service=data_service,
        debug=config.provided.app_debug,
    )

    # FastAPI application instance
    app: FastAPI = providers.Singleton(
        lambda factory: factory.create_app(
            life_span=__import__("app.utils.uitls", fromlist=["lifespan"]).lifespan
        ),
        factory=app_factory,
    )

    def init_app(self) -> None:
        """Discover and wire services after container is built."""
        self.class_store().discover_services(["app.services", "app.api"])
