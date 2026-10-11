"""Outgoing webhooks: tell other systems what happened here, signed and retried.

Administrators subscribe a URL to event types (``user.registered``, ``rbac.*``, ``*``). Every
security event the audit log records is published, and services can publish their own with
``WebhookService.publish(event, data)``. Each delivery is a background job, so it is retried with
backoff and ends visibly in ``/admin/jobs?status=dead`` if the receiver keeps failing.

Requests follow the Standard Webhooks spec (standardwebhooks.com): ``webhook-id`` (stable across
retries, so receivers can de-duplicate), ``webhook-timestamp``, and ``webhook-signature``:
``v1,<base64 HMAC-SHA256 of "<id>.<timestamp>.<body>">``. Signing secrets are encrypted at rest.

Destinations must be https (``webhooks_allow_http`` for local testing) and may not resolve to a
private, loopback or link-local address (``webhooks_allow_private_networks``), so a webhook
cannot be pointed at internal services.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import ipaddress
import json
import secrets
import socket
import time
import uuid
from datetime import UTC, datetime
from fnmatch import fnmatchcase
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

import httpx
from cryptography.fernet import Fernet

from app.services.data.policies import CachePolicy

if TYPE_CHECKING:
    from app.services.audit import AuditService
    from app.services.data import DataService
    from app.services.jobs import JobService
    from app.services.logger import Logger
    from config import Config

COLLECTION = "webhooks"
DELIVER_JOB = "webhook.deliver"
DB = CachePolicy.DB_ONLY
MAX_WEBHOOKS = 50


class WebhookError(ValueError):
    """The webhook request was refused; the message is safe to show."""


def sign(secret: str, message_id: str, timestamp: int, body: bytes) -> str:
    """Standard Webhooks v1 signature (the secret is ``whsec_`` plus base64 key bytes)."""
    key = base64.b64decode(secret.removeprefix("whsec_"))
    payload = f"{message_id}.{timestamp}.".encode() + body
    return "v1," + base64.b64encode(hmac.new(key, payload, hashlib.sha256).digest()).decode()


def _fernet(key: str) -> Fernet:
    # Derived for this purpose only, so the two-factor secrets' key is never reused as-is.
    digest = hashlib.sha256(f"webhooks:{key}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


class WebhookService:
    """Subscriptions, publishing, and the delivery job."""

    def __init__(
        self,
        config: Config,
        logger: Logger,
        data_service: DataService,
        jobs: JobService,
        audit: AuditService,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.logger = logger
        self.data_service = data_service
        self.jobs = jobs
        self.audit = audit
        self.fernet = _fernet(config["mfa_encryption_key"] or "")
        self.timeout: float = config["webhooks_timeout_seconds"]
        self.allow_http: bool = config["webhooks_allow_http"]
        self.allow_private: bool = config["webhooks_allow_private_networks"]
        self.transport = transport
        jobs.handler(DELIVER_JOB)(self.deliver)
        audit.listeners.append(self.publish_audit_event)

    # ---- destinations ----------------------------------------------------------------------
    async def _check_destination(self, url: str) -> None:
        parts = urlsplit(url)
        if parts.scheme not in ("https", "http") or not parts.hostname:
            raise WebhookError("The webhook URL must be an absolute http(s) URL")
        if parts.scheme == "http" and not self.allow_http:
            raise WebhookError("The webhook URL must use https")
        if self.allow_private:
            return
        for address in await self._resolve(parts.hostname, parts.port or 443):
            if not ipaddress.ip_address(address).is_global:
                raise WebhookError("The webhook URL points at a private or internal address")

    @staticmethod
    async def _resolve(host: str, port: int) -> list[str]:
        try:
            infos = await asyncio.get_running_loop().getaddrinfo(host, port)
        except socket.gaierror as e:
            raise WebhookError(f"Cannot resolve {host}") from e
        return [info[4][0] for info in infos]

    # ---- subscriptions ---------------------------------------------------------------------
    async def create(self, url: str, events: list[str], description: str) -> tuple[str, dict]:
        """Subscribe ``url``; returns (the signing secret, shown once; the subscription)."""
        await self._check_destination(url)
        if await self.data_service.count(COLLECTION, {}) >= MAX_WEBHOOKS:
            raise WebhookError(f"There are already {MAX_WEBHOOKS} webhooks; remove one first")
        secret = "whsec_" + base64.b64encode(secrets.token_bytes(32)).decode()
        record = {
            "id": uuid.uuid4().hex,
            "url": url,
            "events": sorted(set(events)),
            "description": description,
            "secret": self.fernet.encrypt(secret.encode()).decode(),
            "created_at": datetime.now(UTC),
        }
        await self.data_service.insert(COLLECTION, record)
        await self.audit.record(
            "webhook.created", target_type="webhook", target_id=record["id"], details={"url": url}
        )
        return secret, self.public_view(record)

    @staticmethod
    def public_view(record: dict[str, Any]) -> dict[str, Any]:
        return {k: record.get(k) for k in ("id", "url", "events", "description", "created_at")}

    async def list_all(self) -> list[dict[str, Any]]:
        records = await self.data_service.find_many(
            COLLECTION, {}, policy=DB, sort=[("created_at", -1)], limit=MAX_WEBHOOKS
        )
        return [self.public_view(r) for r in records]

    async def remove(self, webhook_id: str) -> bool:
        removed = await self.data_service.delete(COLLECTION, {"id": webhook_id}, policy=DB)
        if removed:
            await self.audit.record("webhook.removed", target_type="webhook", target_id=webhook_id)
        return removed

    # ---- publishing ------------------------------------------------------------------------
    async def publish(self, event: str, data: dict[str, Any]) -> int:
        """Queue one delivery per subscription matching ``event``; returns how many."""
        subscriptions = await self.data_service.find_many(
            COLLECTION, {}, policy=DB, limit=MAX_WEBHOOKS
        )
        message = {"type": event, "timestamp": datetime.now(UTC).isoformat(), "data": data}
        queued = 0
        for hook in subscriptions:
            if any(fnmatchcase(event, pattern) for pattern in hook["events"]):
                await self.jobs.enqueue(
                    DELIVER_JOB,
                    {
                        "webhook_id": hook["id"],
                        "message_id": f"msg_{uuid.uuid4().hex}",
                        "message": message,
                    },
                )
                queued += 1
        return queued

    async def send_test(self, webhook_id: str) -> bool:
        """Queue a ``webhook.test`` delivery to one subscription, whatever its event filter."""
        if await self.data_service.get(COLLECTION, {"id": webhook_id}, policy=DB) is None:
            return False
        message = {"type": "webhook.test", "timestamp": datetime.now(UTC).isoformat(), "data": {}}
        await self.jobs.enqueue(
            DELIVER_JOB,
            {"webhook_id": webhook_id, "message_id": f"msg_{uuid.uuid4().hex}", "message": message},
        )
        return True

    async def publish_audit_event(self, event: dict[str, Any]) -> None:
        """Audit listener. Addresses and user agents stay out of webhooks (personal data)."""
        if event["action"].startswith("webhook."):
            return  # never announce webhook changes through webhooks
        await self.publish(
            event["action"],
            {key: event.get(key) for key in ("actor_id", "target_type", "target_id", "details")},
        )

    # ---- delivery (a job handler: raising means "retry later") ------------------------------
    async def deliver(self, payload: dict[str, Any]) -> None:
        hook = await self.data_service.get(COLLECTION, {"id": payload["webhook_id"]}, policy=DB)
        if hook is None:
            return  # unsubscribed since: nothing to do, and nothing to retry
        await self._check_destination(hook["url"])  # DNS may have changed since subscribing
        secret = self.fernet.decrypt(hook["secret"].encode()).decode()
        body = json.dumps(payload["message"], separators=(",", ":"), default=str).encode()
        timestamp = int(time.time())
        headers = {
            "content-type": "application/json",
            "webhook-id": payload["message_id"],
            "webhook-timestamp": str(timestamp),
            "webhook-signature": sign(secret, payload["message_id"], timestamp, body),
        }
        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            response = await client.post(hook["url"], content=body, headers=headers)
        if not response.is_success:
            raise RuntimeError(f"Webhook receiver answered {response.status_code}")
