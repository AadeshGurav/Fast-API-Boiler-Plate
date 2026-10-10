"""Builds every service once and hands them out as a plain object.

This replaces a dependency-injection framework: the dependency graph is short enough to
read top to bottom, so wiring is ordinary constructor calls. The result lives on
``app.state.services``; routes get it through ``app.api.deps``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.services.audit import AuditService
from app.services.auth import AuthService
from app.services.cache import CacheService
from app.services.data import DataService
from app.services.database_service import DatabaseService
from app.services.error.error_service import ErrorService
from app.services.file import FileService
from app.services.file.storage import create_storage
from app.services.jobs import JobService
from app.services.logger import Logger
from app.services.mailer import send_email
from app.services.metrics import MetricsService
from app.services.oauth import OAuthService
from app.services.password_service import PasswordService
from app.services.rbac import RBACService
from app.services.sentry import SentryService
from app.services.tracing import TracingService

if TYPE_CHECKING:
    from app.core.interfaces.storage_interface import StorageInterface
    from config import Config


@dataclass
class Services:
    """Every service of one application instance. Optional ones are None when disabled."""

    config: Config
    logger: Logger
    database_service: DatabaseService
    cache_service: CacheService
    data_service: DataService
    password_service: PasswordService
    audit_service: AuditService
    rbac_service: RBACService
    auth_service: AuthService
    error_service: ErrorService
    storage_backend: StorageInterface
    file_service: FileService
    job_service: JobService
    metrics_service: MetricsService | None = None
    tracing_service: TracingService | None = None
    sentry_service: SentryService | None = None
    oauth_service: OAuthService | None = None


def build_services(config: Config) -> Services:
    """Construct all services from configuration."""
    logger = Logger(config)

    database_service = DatabaseService(config, logger)
    cache_service = CacheService(config, logger)
    data_service = DataService(
        config, logger, database_service=database_service, cache_service=cache_service
    )
    password_service = PasswordService(config, logger)
    audit_service = AuditService(config, logger, data_service)
    rbac_service = RBACService(config, logger, data_service, cache_service, audit_service)
    auth_service = AuthService(
        logger, config, data_service, password_service, rbac_service, audit_service
    )
    storage_backend = create_storage(config, logger)

    def optional(flag: str, build):
        enabled = bool(config.get(flag))
        logger.info(f"{flag}: {'enabled' if enabled else 'disabled'}")
        return build() if enabled else None

    services = Services(
        config=config,
        logger=logger,
        database_service=database_service,
        cache_service=cache_service,
        data_service=data_service,
        password_service=password_service,
        audit_service=audit_service,
        rbac_service=rbac_service,
        auth_service=auth_service,
        error_service=ErrorService(logger, config),
        storage_backend=storage_backend,
        file_service=FileService(logger, config, data_service, storage_backend),
        job_service=JobService(config, logger, data_service),
        metrics_service=optional(
            "metrics_enabled", lambda: MetricsService(logger=logger, config=config)
        ),
        tracing_service=optional(
            "tracing_enabled", lambda: TracingService(logger=logger, config=config)
        ),
        sentry_service=optional(
            "sentry_enabled", lambda: SentryService(logger=logger, config=config)
        ),
        oauth_service=optional(
            "oauth_enabled",
            lambda: OAuthService(config=config, logger=logger, data_service=data_service),
        ),
    )
    register_job_handlers(services)
    return services


def register_job_handlers(services: Services) -> None:
    """Every background job the application knows, in one place (API and ``app.jobs``)."""
    jobs, config, logger = services.job_service, services.config, services.logger

    @jobs.handler("email.send")
    async def send_email_job(payload: dict) -> None:
        # Raising makes the queue retry; send_email reports failure by returning False.
        if not await send_email(config, logger, payload["to"], payload["subject"], payload["body"]):
            raise RuntimeError("SMTP delivery failed")
