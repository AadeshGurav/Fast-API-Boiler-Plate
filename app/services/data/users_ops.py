from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from .policies import CachePolicy

if TYPE_CHECKING:
    from .data_service import DataService


def normalize_user(record: dict[str, Any] | None) -> dict[str, Any] | None:
    """Give a stored user the shape the auth layer expects.

    Handles records written by older versions (``password`` instead of
    ``password_hash``, an integer ``login_attempts`` counter, email only under
    ``profile``) so the rest of the application sees a single format.

    Args:
    ----
        record: User record as returned by the data service.

    Returns:
    -------
        Normalized copy, or None if there is no record.

    """
    if not record:
        return None

    user = record.copy()

    if "password" in user and "password_hash" not in user:
        user["password_hash"] = user.pop("password")

    # Older records stored a single "role" string; the canonical field is "roles".
    legacy_role = user.pop("role", None)
    if not user.get("roles"):
        user["roles"] = [legacy_role] if legacy_role else []

    if "email" not in user:
        profile = user.get("profile")
        if isinstance(profile, dict) and "email" in profile:
            user["email"] = profile["email"]

    # ``login_attempts_history`` is the source of truth; ``login_attempts`` used to
    # be an integer counter.
    history = user.pop("login_attempts_history", None)
    if isinstance(history, list) and history:
        user["login_attempts"] = history
    elif not isinstance(user.get("login_attempts"), list):
        user["login_attempts"] = []

    user.setdefault("sessions", [])
    return user


class UsersOps:
    """User-related data operations built on core CRUD."""

    def __init__(self: UsersOps, service: DataService) -> None:
        """Initialize UsersOps.

        Args:
        ----
            service: DataService instance.

        """
        self.service = service
        self.collection = "users"

    @staticmethod
    def _policy(fresh: bool) -> CachePolicy:
        return CachePolicy.DB_ONLY if fresh else CachePolicy.AUTO

    async def increment_failed_logins(self: UsersOps, user: dict[str, Any]) -> int:
        """Atomically count one more failed login and return the new total.

        Atomic so that parallel guesses cannot all read the same count and slip
        under the lockout threshold.
        """
        count = await self.service.increment(
            self.collection, {"id": user["id"]}, "failed_login_count"
        )
        await self._forget_cached(user)
        return count or 0

    async def _forget_cached(self: UsersOps, user: dict[str, Any] | None) -> None:
        """Drop every cache entry a user can be reached through.

        Users are cached once per lookup key (id, username, email). A write that
        only cleared the entry it used would leave the others serving stale roles,
        status or lock state until the TTL expired.
        """
        if not user:
            return
        for field in ("id", "username", "email"):
            if user.get(field):
                await self.service.delete(
                    self.collection,
                    {field: user[field]},
                    policy=CachePolicy.CACHE_ONLY,
                )

    async def create_user(self: UsersOps, user_data: dict[str, Any]) -> str:
        """Create a new user.

        Args:
        ----
            user_data: User data dictionary.

        Returns:
        -------
            User ID.

        """
        user_id = user_data.get("id") or str(uuid.uuid4())
        now = datetime.now(UTC)
        user_data = {**user_data, "id": user_id, "created_at": now, "updated_at": now}

        await self.service.set(
            self.collection,
            {"id": user_id},
            user_data,
            policy=CachePolicy.DB_ONLY,
        )
        return user_id

    async def get_user_by_id(self: UsersOps, user_id: str, *, fresh: bool = False) -> dict | None:
        """Get user by ID.

        Args:
        ----
            user_id: User ID.

        Returns:
        -------
            User dictionary or None if not found.

        """
        return normalize_user(
            await self.service.get(self.collection, {"id": user_id}, policy=self._policy(fresh))
        )

    async def get_user_by_username(
        self: UsersOps, username: str, *, fresh: bool = False
    ) -> dict | None:
        """Get user by username.

        Args:
        ----
            username: Username.

        Returns:
        -------
            User dictionary or None if not found.

        """
        return normalize_user(
            await self.service.get(
                self.collection, {"username": username}, policy=self._policy(fresh)
            )
        )

    async def get_user_by_email(self: UsersOps, email: str, *, fresh: bool = False) -> dict | None:
        """Get user by email.

        Args:
        ----
            email: Email address.

        Returns:
        -------
            User dictionary or None if not found.

        """
        return normalize_user(
            await self.service.get(self.collection, {"email": email}, policy=self._policy(fresh))
        )

    async def list_users(
        self, *, limit: int, skip: int, status: str | None = None
    ) -> tuple[list[dict], int]:
        """A page of users, newest first, plus the total matching count."""
        filters = {"status": status} if status else {}
        users = await self.service.find_many(
            self.collection, filters, limit=limit, skip=skip, sort=[("created_at", -1)]
        )
        return [normalize_user(u) for u in users], await self.service.count(
            self.collection, filters
        )

    async def update_user(self: UsersOps, user_id: str, updates: dict[str, Any]) -> bool:
        """Update an existing user.

        Args:
        ----
            user_id: User ID.
            updates: Update dictionary.

        Returns:
        -------
            True if the user exists and was updated, False otherwise.

        """
        # Read from the database, not the cache: we need the keys the *old*
        # record is cached under (username/email may be what is changing).
        before = await self.service.get(
            self.collection, {"id": user_id}, policy=CachePolicy.DB_ONLY
        )
        if before is None:
            return False

        updates = {**updates, "updated_at": datetime.now(UTC)}
        updated = await self.service.update(
            self.collection, {"id": user_id}, updates, policy=CachePolicy.DB_ONLY
        )
        await self._forget_cached(before)
        await self._forget_cached({**before, **updates})
        return updated

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user and every cache entry they can be reached through."""
        before = await self.service.get(
            self.collection, {"id": user_id}, policy=CachePolicy.DB_ONLY
        )
        deleted = await self.service.delete(
            self.collection, {"id": user_id}, policy=CachePolicy.DB_ONLY
        )
        await self._forget_cached(before)
        return deleted
