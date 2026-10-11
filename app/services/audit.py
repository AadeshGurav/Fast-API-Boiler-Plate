"""Security audit log: who changed what, when, and from where.

Services call ``AuditService.record`` after a security-relevant change succeeds: roles, groups
and grants, account status and deletion, passwords, sessions, MFA and API tokens. The actor,
client address and user agent come from the request context, which ``RBACMiddleware`` sets,
so services do not have to pass them around. The request id ties an event to its log lines.

Sign-in attempts stay in ``login_attempts`` (they drive lockout); this log covers changes.
Writing an event never blocks or fails the action it describes: a failed write is logged.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar, Token
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.services.base_service import BaseService
from app.services.data import cursor as keyset
from app.services.logger import request_id_var

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from app.services.data import DataService
    from app.services.logger import Logger
    from config import Config

COLLECTION = "audit_events"
MAX_DETAIL_LENGTH = 200


@dataclass(frozen=True)
class AuditActor:
    """The caller of the current request."""

    user_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None


audit_actor_var: ContextVar[AuditActor | None] = ContextVar("audit_actor", default=None)


def set_audit_actor(actor: AuditActor) -> Token[AuditActor | None]:
    """Attribute every event recorded in this context to ``actor``; returns a reset token."""
    return audit_actor_var.set(actor)


def _clip(details: dict[str, Any]) -> dict[str, Any]:
    """Keep details small and flat: identifiers and counts, never payloads or secrets."""
    clipped: dict[str, Any] = {}
    for key, value in details.items():
        if isinstance(value, bool | int | float) or value is None:
            clipped[key] = value
        else:
            clipped[key] = str(value)[:MAX_DETAIL_LENGTH]
    return clipped


class AuditService(BaseService):
    """Append-only security events, kept for ``audit_retention_days``."""

    def __init__(self, config: Config, logger: Logger, data_service: DataService) -> None:
        super().__init__(config, logger)
        self.data_service = data_service
        # Called with each stored event (e.g. webhooks); a failing listener is logged, never raised.
        self.listeners: list[Callable[[dict[str, Any]], Awaitable[None]]] = []

    async def record(
        self,
        action: str,
        *,
        target_type: str,
        target_id: str | None = None,
        actor_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Append one event. ``actor_id`` overrides the request's caller (e.g. registration,
        where the new account is the actor). Never raises."""
        actor = audit_actor_var.get() or AuditActor()
        event = {
            "id": uuid.uuid4().hex,
            "at": datetime.now(UTC),
            "action": action,
            "actor_id": actor_id or actor.user_id,
            "target_type": target_type,
            "target_id": target_id,
            "ip_address": actor.ip_address,
            "user_agent": (actor.user_agent or "")[:MAX_DETAIL_LENGTH] or None,
            "request_id": request_id_var.get(),
            "details": _clip(details or {}),
        }
        try:
            await self.data_service.insert(COLLECTION, event)
        except Exception as e:
            # Deliberate: an audit outage must not lock users out of their own accounts.
            self.logger.error(
                f"Audit event not recorded: {action}: {e}",
                extra={"service": "AuditService", "action": action, "target_id": target_id},
            )
            return
        for listener in self.listeners:
            try:
                await listener(event)
            except Exception as e:  # deliberate: a listener never fails the change
                self.logger.error(
                    f"Audit listener failed for {action}: {e}",
                    extra={"service": "AuditService", "action": action, "target_id": target_id},
                )

    async def list_events(
        self,
        *,
        actor_id: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        action: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], int, str | None]:
        """Newest first, filtered; returns (page of events, total matching, next cursor).
        With ``cursor``, ``page`` is ignored."""
        filters: dict[str, Any] = {
            key: value
            for key, value in {
                "actor_id": actor_id,
                "target_type": target_type,
                "target_id": target_id,
                "action": action,
            }.items()
            if value is not None
        }
        window = {op: value for op, value in (("$gt", since), ("$lt", until)) if value}
        if window:
            filters["at"] = window
        query = {"$and": [filters, keyset.after(cursor, "at", "id")]} if cursor else filters
        rows = await self.data_service.find_many(
            COLLECTION,
            query,
            sort=keyset.newest_first("at", "id"),
            skip=0 if cursor else (page - 1) * page_size,
            limit=page_size + 1,
        )
        events = rows[:page_size]
        next_cursor = keyset.encode(events[-1], "at", "id") if len(rows) > page_size else None
        return events, await self.data_service.count(COLLECTION, filters), next_cursor
