"""Sentry error reporting via the SDK's own FastAPI/Starlette integrations.

The integrations already capture unhandled exceptions with request data, so no middleware is
needed. PII is not sent (``send_default_pii=False``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.pymongo import PyMongoIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.scrubber import DEFAULT_DENYLIST, EventScrubber

from app.services.base_service import BaseService

if TYPE_CHECKING:
    from app.services.logger import Logger
    from config import Config


class SentryService(BaseService):
    """Initializes the Sentry SDK from configuration (``sentry_dsn`` and friends)."""

    def __init__(self, logger: Logger, config: Config) -> None:
        super().__init__(config, logger)
        self.dsn: str | None = config["sentry_dsn"]
        self.enabled = bool(self.dsn)
        if not self.enabled:
            logger.warning("sentry_enabled is on but sentry_dsn is not set: nothing is reported")
            return
        sentry_sdk.init(
            dsn=self.dsn,
            environment=config["sentry_environment"],
            release=config["app_version"],
            traces_sample_rate=config["sentry_traces_sample_rate"],
            profiles_sample_rate=config["sentry_profiles_sample_rate"],
            send_default_pii=False,
            # Never ship request bodies: they carry passwords (new_password, ...) that the
            # SDK's default denylist does not know. The scrubber is a second line.
            max_request_body_size="never",
            event_scrubber=EventScrubber(
                denylist=[*DEFAULT_DENYLIST, "new_password", "current_password", "refresh_token"],
                recursive=True,
            ),
            integrations=[
                FastApiIntegration(),
                HttpxIntegration(),
                RedisIntegration(),
                PyMongoIntegration(),
            ],
        )
        logger.info("Sentry initialized")

    def is_enabled(self) -> bool:
        """Whether events are being reported."""
        return self.enabled

    def flush(self, timeout: float = 2.0) -> None:
        """Send queued events (call on shutdown)."""
        if self.enabled:
            sentry_sdk.flush(timeout)


def set_user(user_id: str, username: str | None = None) -> None:
    """Attach the authenticated user to subsequent events (no-op while Sentry is off)."""
    sentry_sdk.set_user({"id": user_id, "username": username})


__all__ = ["SentryService", "set_user"]
