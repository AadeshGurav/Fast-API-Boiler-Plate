"""Application lifecycle and request helpers."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import random
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from user_agents import parse

from app.models.session import DeviceInfo

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi import FastAPI, Request


async def purge_abandoned_uploads_forever(services) -> None:
    """Every ``file_cleanup_interval`` seconds, drop chunked-upload data nobody finished.

    Every worker runs this; the purge is idempotent, and the random first delay keeps
    them from all hitting the storage backend together. A failed pass is logged and
    retried next time rather than ending the task.
    """
    interval = services.config["file_cleanup_interval"]
    handler = services.file_service.chunked_upload_handler
    await asyncio.sleep(random.uniform(0, interval))  # noqa: S311 - jitter, not security
    while True:
        try:
            removed = await handler.purge_abandoned()
            if removed:
                services.logger.info(f"Purged {removed} abandoned upload file(s)")
        except Exception as e:
            services.logger.error(f"Upload cleanup failed: {e}")
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Connect the data layer on startup; release everything on shutdown."""
    from app.services.auth.bootstrap import ensure_bootstrap_admin

    services = app.state.services
    logger = services.logger
    logger.info("Starting application")

    await services.data_service.connect()
    try:
        await ensure_bootstrap_admin(services.auth_service, services.config, logger)
    except Exception as e:
        logger.error(f"Bootstrap admin creation failed: {e}")

    oauth = services.oauth_service
    if oauth is not None and oauth.oauth_enabled:
        logger.info(f"OAuth providers: {list(oauth.providers)}")
    logger.info("Application started")

    janitor = (
        asyncio.create_task(purge_abandoned_uploads_forever(services))
        if services.config["file_cleanup_interval"]
        else None
    )
    try:
        yield
    finally:
        logger.info("Shutting down")
        if janitor is not None:
            janitor.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await janitor
        await services.data_service.close()
        if services.sentry_service is not None:
            services.sentry_service.flush()
        logger.shutdown()


def client_ip(request: Request) -> str:
    """The caller's IP address, resistant to header spoofing.

    ``X-Forwarded-For`` is client-controlled unless a reverse proxy we trust appended
    to it. Set ``trusted_proxy_count`` (the number of proxies in front of the app) to
    use it: the address is then taken that many entries from the right, which is the
    last one a trusted proxy wrote. With the default of 0 only the socket peer is used.
    """
    peer = request.client.host if request.client else "unknown"
    config = getattr(request.app.state, "services", None)
    trusted_proxies = config.config["trusted_proxy_count"] if config else 0
    if not trusted_proxies:
        return peer

    hops = [h.strip() for h in request.headers.get("x-forwarded-for", "").split(",") if h.strip()]
    return hops[-trusted_proxies] if len(hops) >= trusted_proxies else peer


def extract_device_info(request: Request) -> DeviceInfo:
    """Describe the caller's device from the request."""
    user_agent = request.headers.get("user-agent", "")
    ip_address = client_ip(request)
    language = request.headers.get("accept-language")
    agent = parse(user_agent)

    fingerprint_source = f"{ip_address}|{user_agent[:200]}|{language or ''}"
    return DeviceInfo(
        user_agent=user_agent,
        ip_address=ip_address,
        fingerprint=hashlib.sha256(fingerprint_source.encode()).hexdigest()[:32],
        platform=agent.os.family,
        os_version=agent.os.version_string,
        browser=agent.browser.family,
        browser_version=agent.browser.version_string,
        device_type="Mobile" if agent.is_mobile else "Tablet" if agent.is_tablet else "PC",
        language=language,
        is_bot=agent.is_bot,
        geo_location=None,
    )
