from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from app.services.base_service import BaseService
from app.services.cache import CacheService
from app.services.database_service import DatabaseService
from app.services.logger import Logger
from config import Config

from .policies import CachePolicy


def _normalize_record(record: dict[str, Any] | None) -> dict[str, Any] | None:
    """Normalize MongoDB record to application format.

    Args:
    ----
        record: MongoDB record dictionary.

    Returns:
    -------
        Application-compatible record dictionary.

    """
    if not record:
        return None

    normalized = record.copy()
    if "_id" in normalized:
        normalized["id"] = str(normalized.pop("_id"))

    if "password" in normalized and "password_hash" not in normalized:
        normalized["password_hash"] = normalized.pop("password")

    if "email" not in normalized and "profile" in normalized:
        profile = normalized.get("profile", {})
        if isinstance(profile, dict) and "email" in profile:
            normalized["email"] = profile["email"]

    # Handle login_attempts - convert from int to list if needed (for User model)
    if "login_attempts" in normalized and isinstance(normalized["login_attempts"], int):
        # Old format: convert integer counter to empty list
        normalized["login_attempts"] = []

    # Handle login_attempts_history (new format) - prioritize it as source of truth
    if "login_attempts_history" in normalized:
        history = normalized["login_attempts_history"]
        if isinstance(history, list) and len(history) > 0:
            # login_attempts_history is source of truth - use it
            normalized["login_attempts"] = history
        # Remove the history field after merging
        normalized.pop("login_attempts_history", None)
    elif "login_attempts" not in normalized:
        # No history and no attempts - initialize empty list
        normalized["login_attempts"] = []

    # Ensure sessions array exists
    if "sessions" not in normalized:
        normalized["sessions"] = []

    def _convert_datetime_strings(obj: Any) -> Any:
        """Recursively convert datetime strings to datetime objects."""
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                if isinstance(value, str) and (
                    key.endswith("_at") or key.endswith("_date") or key == "exp"
                ):
                    try:
                        value = value.replace("Z", "+00:00")
                        result[key] = datetime.fromisoformat(value)
                    except (ValueError, AttributeError):
                        result[key] = _convert_datetime_strings(value)
                else:
                    result[key] = _convert_datetime_strings(value)
            return result
        elif isinstance(obj, list):
            return [_convert_datetime_strings(item) for item in obj]
        return obj

    normalized = _convert_datetime_strings(normalized)

    return normalized


def _default_cache_key(collection: str, filters: dict[str, Any]) -> str:
    """Generate default cache key from collection and filters.

    Args:
    ----
        collection: Collection name.
        filters: Filter dictionary.

    Returns:
    -------
        MD5 hash of collection and filters as cache key.

    """
    payload = json.dumps([collection, filters], sort_keys=True, default=str)
    return hashlib.md5(payload.encode()).hexdigest()


class DataService(BaseService):
    """Core data access service with cache-aware CRUD operations.

    This class is intentionally small and delegates domain logic to ops modules.
    """

    def __init__(
        self: DataService,
        config: Config,
        logger: Logger,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize DataService.

        Args:
        ----
            config: Configuration instance.
            logger: Logger instance.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        """
        super().__init__(config, logger, *args, **kwargs)

        # Wire underlying services
        from app.database.mongodb import MongoDB
        from app.database.redis import Redis

        database_provider = config.get("app_database_provider")
        cache_provider = config.get("app_cache_provider")

        if database_provider == "mongodb":
            db_backend = MongoDB(
                host=config.get("mongo_host"),
                port=config.get("mongo_port"),
                db_name=config.get("app_database"),
                logger=logger,
                config=config,
            )
        elif database_provider == "redis":
            db_backend = Redis(
                host=config.get("redis_host"),
                port=config.get("redis_port"),
                db_name=config.get("app_database"),
                logger=logger,
                config=config,
            )
        # Add more if required
        else:
            raise ValueError(f"Invalid database provider: {database_provider}")

        if cache_provider == "redis":
            cache_backend = Redis(
                host=config.get("redis_host"),
                port=config.get("redis_port"),
                db_name=config.get("app_database"),
                password=config.get("redis_password"),
                logger=logger,
                config=config,
            )
        else:
            raise ValueError(f"Invalid cache provider: {cache_provider}")

        self.database_service = DatabaseService(config=config, logger=logger, backend=db_backend)
        self.cache_service = CacheService(config, logger, cache_backend)

        # Attach ops (lazy imported to keep this file small)
        try:
            from . import users_ops

            self.users = users_ops.UsersOps(self)
        except ImportError as e:
            self.logger.warning(f"Failed to import users_ops: {e}")
            self.users = None

        try:
            from . import sessions_ops

            self.sessions = sessions_ops.SessionsOps(self)
        except ImportError as e:
            self.logger.warning(f"Failed to import sessions_ops: {e}")
            self.sessions = None

        try:
            from . import rbac_ops

            self.rbac = rbac_ops.RBACOps(self)
        except ImportError as e:
            self.logger.warning(f"Failed to import rbac_ops: {e}")
            self.rbac = None

        try:
            from . import oauth_ops

            self.oauth = oauth_ops.OAuthOps(self)
        except ImportError as e:
            self.logger.warning(f"Failed to import oauth_ops: {e}")
            self.oauth = None

        try:
            from . import files_ops

            self.files = files_ops.FilesOps(self)
        except ImportError as e:
            self.logger.warning(f"Failed to import files_ops: {e}")
            self.files = None

        self.logger.info("DataService initialized", extra={"service": "DataService"})

    # ---- Lifecycle -----------------------------------------------------
    async def connect(self: DataService) -> None:
        """Connect to database and cache backends.

        Returns
        -------
            None

        """
        await self.database_service.connect()
        await self.cache_service.connect()
        await self.database_service.initialize_application_data(self.config)
        self.logger.info("DataService: All backends connected and initialized.")

    async def close(self: DataService) -> None:
        """Close database and cache backends.

        Returns
        -------
            None

        """
        await self.database_service.close()
        await self.cache_service.close()
        self.logger.info("DataService: All backends closed.")

    # ---- Core CRUD with cache policy ----------------------------------
    async def get(
        self: DataService,
        collection: str,
        filters: dict[str, Any],
        *,
        key: str | None = None,
        policy: CachePolicy = CachePolicy.AUTO,
    ) -> dict[str, Any] | None:
        """Get a record from collection with cache policy.

        Args:
        ----
            collection: Collection name.
            filters: Filter dictionary.
            key: Optional cache key.
            policy: Cache policy to use.

        Returns:
        -------
            Record dictionary or None if not found.

        """
        cache_key = key or _default_cache_key(collection, filters)

        if policy == CachePolicy.CACHE_ONLY:
            cached = await self.cache_service.get(cache_key)
            return _normalize_record(cached)

        if policy == CachePolicy.AUTO:
            cached = await self.cache_service.get(cache_key)
            if cached is not None:
                return _normalize_record(cached)

        # DB_ONLY or cache miss
        record = await self.database_service.get_record(collection, filters)
        if record is not None and policy != CachePolicy.DB_ONLY:
            await self.cache_service.set(cache_key, record)
        return _normalize_record(record)

    async def find_many(
        self: DataService,
        collection: str,
        filters: dict[str, Any],
        *,
        key: str | None = None,
        policy: CachePolicy = CachePolicy.DB_ONLY,
    ) -> list[dict]:
        """Find multiple records from collection with cache policy.

        Args:
        ----
            collection: Collection name.
            filters: Filter dictionary.
            key: Optional cache key.
            policy: Cache policy to use.

        Returns:
        -------
            List of record dictionaries.

        """
        # By default, lists come from DB to avoid cache stampede complexity
        if policy == CachePolicy.CACHE_ONLY:
            cached = await self.cache_service.get(
                key or _default_cache_key(collection, filters)
            )
            if cached:
                return [_normalize_record(record) for record in cached]
            return []
        records = await self.database_service.find_many(collection, filters)
        if policy == CachePolicy.AUTO:
            await self.cache_service.set(
                key or _default_cache_key(collection, filters), records
            )
        # Normalize all records before returning
        return [_normalize_record(record) for record in (records or [])]

    async def set(
        self: DataService,
        collection: str,
        filters: dict[str, Any],
        data: dict[str, Any],
        *,
        key: str | None = None,
        policy: CachePolicy = CachePolicy.AUTO,
        ttl: int | None = None,
    ) -> bool:
        """Set/upsert a record in collection with cache policy.

        Args:
        ----
            collection: Collection name.
            filters: Filter dictionary.
            data: Data dictionary to set.
            key: Optional cache key.
            policy: Cache policy to use.
            ttl: Optional TTL for cache.

        Returns:
        -------
            True if successful, False otherwise.

        """
        cache_key = key or _default_cache_key(collection, filters)

        if policy == CachePolicy.CACHE_ONLY:
            await self.cache_service.set(cache_key, data, ttl)
            return True

        # Write to DB
        result = await self.database_service.upsert_record(collection, filters, data)
        if result and policy != CachePolicy.DB_ONLY:
            await self.cache_service.set(cache_key, data, ttl)
        return result

    async def delete(
        self: DataService,
        collection: str,
        filters: dict[str, Any],
        *,
        key: str | None = None,
        policy: CachePolicy = CachePolicy.AUTO,
    ) -> bool:
        """Delete a record from collection with cache policy.

        Args:
        ----
            collection: Collection name.
            filters: Filter dictionary.
            key: Optional cache key.
            policy: Cache policy to use.

        Returns:
        -------
            True if successful, False otherwise.

        """
        cache_key = key or _default_cache_key(collection, filters)

        if policy == CachePolicy.CACHE_ONLY:
            await self.cache_service.delete(cache_key)
            return True

        result = await self.database_service.delete_record(collection, filters)
        if result and policy != CachePolicy.DB_ONLY:
            await self.cache_service.delete(cache_key)
        return result

    # Facade passthroughs for ops (to minimize app changes)
    # USERS
    async def create_user(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Create a user.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            User ID.

        """
        return await self.users.create_user(*args, **kwargs)

    async def get_user_by_id(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Get user by ID.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            User dictionary or None.

        """
        return await self.users.get_user_by_id(*args, **kwargs)

    async def get_user_by_username(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Get user by username.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            User dictionary or None.

        """
        return await self.users.get_user_by_username(*args, **kwargs)

    async def get_user_by_email(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Get user by email.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            User dictionary or None.

        """
        return await self.users.get_user_by_email(*args, **kwargs)

    async def update_user(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Update user.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            True if successful, False otherwise.

        """
        return await self.users.update_user(*args, **kwargs)

    async def delete_user(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Delete user.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            True if successful, False otherwise.

        """
        return await self.users.delete_user(*args, **kwargs)

    # SESSIONS
    async def create_session(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Create a session.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            Session ID.

        """
        return await self.sessions.create_session(*args, **kwargs)

    async def get_session(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Get session by ID.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            Session dictionary or None.

        """
        return await self.sessions.get_session(*args, **kwargs)

    async def get_user_sessions(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Get all sessions for a user.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            List of session dictionaries.

        """
        return await self.sessions.get_user_sessions(*args, **kwargs)

    async def update_session(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Update session.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            True if successful, False otherwise.

        """
        return await self.sessions.update_session(*args, **kwargs)

    async def revoke_session(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Revoke session.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            True if successful, False otherwise.

        """
        return await self.sessions.revoke_session(*args, **kwargs)

    async def revoke_user_sessions(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Revoke all sessions for a user.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            Number of sessions revoked.

        """
        return await self.sessions.revoke_user_sessions(*args, **kwargs)

    # RBAC
    async def sync_roles_to_db(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Sync roles to database.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            True if successful, False otherwise.

        """
        return await self.rbac.sync_roles_to_db(*args, **kwargs)

    async def sync_permissions_to_db(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Sync permissions to database.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            True if successful, False otherwise.

        """
        return await self.rbac.sync_permissions_to_db(*args, **kwargs)

    async def sync_groups_to_db(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Sync groups to database.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            True if successful, False otherwise.

        """
        return await self.rbac.sync_groups_to_db(*args, **kwargs)

    async def get_role(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Get role by ID.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            Role dictionary or None.

        """
        return await self.rbac.get_role(*args, **kwargs)

    async def get_permission(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Get permission by ID.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            Permission dictionary or None.

        """
        return await self.rbac.get_permission(*args, **kwargs)

    async def get_group(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Get group by ID.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            Group dictionary or None.

        """
        return await self.rbac.get_group(*args, **kwargs)

    async def create_temporary_permission(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Create temporary permission.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            Temporary permission ID.

        """
        return await self.rbac.create_temporary_permission(*args, **kwargs)

    async def get_active_temporary_permissions(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Get active temporary permissions.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            List of temporary permission dictionaries.

        """
        return await self.rbac.get_active_temporary_permissions(*args, **kwargs)

    async def revoke_temporary_permission(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Revoke temporary permission.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            True if successful, False otherwise.

        """
        return await self.rbac.revoke_temporary_permission(*args, **kwargs)

    # OAUTH
    async def link_oauth_account(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Link OAuth account.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            True if successful, False otherwise.

        """
        return await self.oauth.link_oauth_account(*args, **kwargs)

    async def get_oauth_account(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Get OAuth account.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            OAuth account dictionary or None.

        """
        return await self.oauth.get_oauth_account(*args, **kwargs)

    async def get_user_oauth_accounts(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Get all OAuth accounts for a user.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            List of OAuth account dictionaries.

        """
        return await self.oauth.get_user_oauth_accounts(*args, **kwargs)

    async def unlink_oauth_account(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Unlink OAuth account.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            True if successful, False otherwise.

        """
        return await self.oauth.unlink_oauth_account(*args, **kwargs)

    async def update_oauth_tokens(
        self: DataService, *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> Any:
        """Update OAuth tokens.

        Args:
        ----
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
        -------
            True if successful, False otherwise.

        """
        return await self.oauth.update_oauth_tokens(*args, **kwargs)


__all__ = ["DataService"]
