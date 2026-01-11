from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from app.services.base_service import BaseService

if TYPE_CHECKING:
    from app.services.logger import Logger
    from config import Config


class DatabaseService(BaseService):
    """Unified database service that wraps a DatabaseInterface backend (MongoDB, PostgreSQL, SQLite, etc.).
    Provides a consistent async API for CRUD and query operations.
    """

    def __init__(
        self: DatabaseService,
        config: Config,
        logger: Logger,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize the DatabaseService.

        Args:
        ----
            config: The configuration to use.
            logger: The logger to use.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        """
        super().__init__(config, logger, *args, **kwargs)

        database_provider = config.get("app_database_provider")

        if database_provider == "mongodb":
            from app.database.mongodb import MongoDB

            self.backend: MongoDB = MongoDB(
                host=config.get("mongo_host"),
                port=config.get("mongo_port"),
                db_name=config.get("app_database"),
                logger=logger,
                config=config,
            )
        elif database_provider == "redis":
            from app.database.redis import Redis

            self.backend: Redis = Redis(
                host=config.get("redis_host"),
                port=config.get("redis_port"),
                db_name=config.get("app_database"),
                logger=logger,
                config=config,
            )
        # Add more if required
        else:
            raise ValueError(f"Invalid database provider: {database_provider}")

        self.logger.info(
            "DatabaseService initialized", extra={"service": "DatabaseService"}
        )

    async def get_record(
        self: DatabaseService, collection: str, filters: dict[str, Any]
    ) -> dict | None:
        """Fetch a single record from the database.

        Args:
        ----
            collection: The collection to fetch the record from.
            filters: The filters to apply to the record.

        Returns:
        -------
            The record or None.

        """
        try:
            record = await self.backend.get_record(collection, filters)
            self.logger.debug(
                f"Fetched record from {collection} with filters {filters}: {record}"
            )
            return record
        except Exception as e:
            self.logger.error(f"Error fetching record: {e}")
            raise

    async def find_many(
        self: DatabaseService, collection: str, filters: dict[str, Any]
    ) -> list[dict]:
        """Fetch multiple records from the database.

        Args:
        ----
            collection: The collection to fetch the records from.
            filters: The filters to apply to the records.

        Returns:
        -------
            The records.

        """
        try:
            records = await self.backend.find_many(collection, filters)
            self.logger.debug(
                f"Fetched {len(records)} records from {collection} with filters {filters}"
            )
            return records
        except Exception as e:
            self.logger.error(f"Error fetching records: {e}")
            raise

    async def insert_record(self: DatabaseService, collection: str, data: dict) -> bool:
        """Insert a new record into the database.

        Args:
        ----
            collection: The collection to insert the record into.
            data: The data to insert into the record.

        Returns:
        -------
            True if the record was inserted, False otherwise.

        """
        try:
            if hasattr(self.backend, "insert_record"):
                result = await self.backend.insert_record(collection, data)
            else:
                # Fallback for backends without insert_record
                result = await self.backend.execute_query(
                    f"INSERT INTO {collection} VALUES (:data)", {"data": data}
                )
            self.logger.debug(f"Inserted record into {collection}: {data}")
            return result
        except Exception as e:
            self.logger.error(f"Error inserting record: {e}")
            raise

    async def update_record(
        self: DatabaseService, collection: str, filters: dict[str, Any], data: dict
    ) -> bool:
        """Update a record in the database.

        Args:
        ----
            collection: The collection to update the record in.
            filters: The filters to apply to the record.
            data: The data to update the record with.

        Returns:
        -------
            True if the record was updated, False otherwise.

        """
        try:
            if hasattr(self.backend, "update_record"):
                result = await self.backend.update_record(collection, filters, data)
            else:
                # Fallback: delete + insert (not atomic)  # noqa: ERA001
                await self.delete_record(collection, filters)
                result = await self.insert_record(collection, data)
            self.logger.debug(
                f"Updated record in {collection} with filters {filters}: {data}"
            )
            return result
        except Exception as e:
            self.logger.error(f"Error updating record: {e}")
            raise

    async def delete_record(
        self: DatabaseService, collection: str, filters: dict[str, Any]
    ) -> bool:
        """Delete a record from the database.

        Args:
        ----
            collection: The collection to delete the record from.
            filters: The filters to apply to the record.

        Returns:
        -------
            True if the record was deleted, False otherwise.

        """
        try:
            if hasattr(self.backend, "delete_record"):
                result = await self.backend.delete_record(collection, filters)
            else:
                # Fallback for backends without delete_record
                result = await self.backend.execute_query(
                    f"DELETE FROM {collection} WHERE ...", filters
                )
            self.logger.debug(
                f"Deleted record from {collection} with filters {filters}"
            )
            return result
        except Exception as e:
            self.logger.error(f"Error deleting record: {e}")
            raise

    async def upsert_record(
        self: DatabaseService, collection: str, filters: dict[str, Any], data: dict
    ) -> bool:
        """Upsert (update or insert) a record in the database.

        Args:
        ----
            collection: The collection to upsert the record in.
            filters: The filters to apply to the record.
            data: The data to upsert into the record.

        Returns:
        -------
            True if the record was upserted, False otherwise.

        """
        try:
            if hasattr(self.backend, "upsert_record"):
                result = await self.backend.upsert_record(collection, filters, data)
            else:
                # Fallback: update, if not found then insert
                updated = await self.update_record(collection, filters, data)
                if not updated:
                    result = await self.insert_record(collection, data)
                else:
                    result = updated
            self.logger.debug(
                f"Upserted record in {collection} with filters {filters}: {data}"
            )
            return result
        except Exception as e:
            self.logger.error(f"Error upserting record: {e}")
            raise

    async def execute_query(
        self: DatabaseService, query: str, params: dict[str, Any]
    ) -> Any:
        """Execute a raw query on the database.

        Args:
        ----
            query: The query to execute.
            params: The parameters to pass to the query.

        Returns:
        -------
            The result of the query.

        """
        try:
            result = await self.backend.execute_query(query, params)
            self.logger.debug(f"Executed query: {query} with params: {params}")
            return result
        except Exception as e:
            self.logger.error(f"Error executing query: {e}")
            raise

    async def connect(self: DatabaseService) -> None:
        """Connect to the database backend."""
        try:
            await self.backend.connect()
            self.logger.info("DatabaseService connected to backend.")
        except Exception as e:
            self.logger.error(f"DatabaseService failed to connect: {e}")
            raise

    async def close(self: DatabaseService) -> None:
        """Close the database backend connection."""
        try:
            await self.backend.close()
            self.logger.info("DatabaseService closed backend connection.")
        except Exception as e:
            self.logger.error(f"DatabaseService failed to close: {e}")
            raise

    async def initialize_application_data(self: DatabaseService) -> None:
        """Initialize application data including default admin user and RBAC structure.

        This method is database-agnostic and works with any backend that implements
        the DatabaseInterface.

        """
        try:
            self.logger.info("Initializing application data...")

            # Initialize database structure first
            await self.backend.initialize_db()

            # Create default admin user if no users exist
            existing_users = await self.find_many("users", {})
            if not existing_users:
                await self._create_default_admin_user()
                self.logger.info("Created default admin user")

            # Initialize RBAC structure
            await self._initialize_rbac_structure()

            # Create default settings if they don't exist
            existing_settings = await self.find_many("settings", {})
            if not existing_settings:
                await self._create_default_settings()
                self.logger.info("Created default settings")

            self.logger.info("Application data initialization completed")

        except Exception as e:
            self.logger.error(f"Application data initialization failed: {str(e)}")
            raise

    async def _create_default_admin_user(self: DatabaseService) -> None:
        """Create the default admin user based on current RBAC structure."""
        # Default admin user with proper RBAC structure
        default_admin = {
            "username": "admin",
            "password": (
                "$argon2id$v=19$m=65536,t=3,p=4$fa8VgpASotRa671XSglhjA$"
                "EgJ3UQ5SQ4ge+oJPB5YbKHIpa85WDFlQwoVZpkadrtg"
            ),  # noqa: E501; passwd is admin
            "role": "admin",
            "groups": ["admins"],
            "permissions": ["*"],  # All permissions
            "tokens": [],
            "theme": "light",
            "profile": {
                "first_name": "System",
                "last_name": "Administrator",
                "email": "admin@oneconf.com",
                "phone": None,
                "avatar": None,
            },
            "preferences": {
                "language": "en",
                "timezone": "UTC",
                "notifications": {
                    "email": True,
                    "push": False,
                    "sms": False,
                },
            },
            "status": "active",
            "last_login": None,
            "login_attempts": 0,
            "locked_until": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        await self.insert_record("users", default_admin)

    async def _initialize_rbac_structure(self: DatabaseService) -> None:
        """Initialize RBAC roles, permissions, and groups."""
        # Initialize roles
        await self._initialize_roles()

        # Initialize permissions
        await self._initialize_permissions()

        # Initialize groups
        await self._initialize_groups()

    async def _initialize_roles(self: DatabaseService) -> None:
        """Initialize default roles."""
        roles = [
            {
                "id": "admin",
                "name": "Administrator",
                "permissions": ["*"],
                "inherits": [],
                "metadata": {"level": 100, "description": "Full system access"},
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "id": "manager",
                "name": "Manager",
                "permissions": [
                    "users:read",
                    "users:write",
                    "reports:read",
                    "reports:write",
                ],
                "inherits": ["user"],
                "metadata": {"level": 50, "description": "Management access"},
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "id": "user",
                "name": "User",
                "permissions": ["profile:read", "profile:write", "dashboard:read"],
                "inherits": [],
                "metadata": {"level": 10, "description": "Basic user access"},
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "id": "guest",
                "name": "Guest",
                "permissions": ["public:read"],
                "inherits": [],
                "metadata": {"level": 1, "description": "Limited guest access"},
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
        ]

        for role in roles:
            existing_role = await self.get_record("roles", {"id": role["id"]})
            if not existing_role:
                await self.insert_record("roles", role)

    async def _initialize_permissions(self: DatabaseService) -> None:
        """Initialize default permissions."""
        permissions = [
            {
                "id": "*",
                "name": "All Permissions",
                "description": "Wildcard permission granting access to everything",
                "resource": "*",
                "action": "*",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "id": "users:read",
                "name": "Read Users",
                "description": "View user information and lists",
                "resource": "users",
                "action": "read",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "id": "users:write",
                "name": "Write Users",
                "description": "Create, update, and delete users",
                "resource": "users",
                "action": "write",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "id": "reports:read",
                "name": "Read Reports",
                "description": "View reports and analytics",
                "resource": "reports",
                "action": "read",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "id": "reports:write",
                "name": "Write Reports",
                "description": "Create and modify reports",
                "resource": "reports",
                "action": "write",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "id": "profile:read",
                "name": "Read Profile",
                "description": "View own profile information",
                "resource": "profile",
                "action": "read",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "id": "profile:write",
                "name": "Write Profile",
                "description": "Update own profile information",
                "resource": "profile",
                "action": "write",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "id": "dashboard:read",
                "name": "Read Dashboard",
                "description": "View dashboard and widgets",
                "resource": "dashboard",
                "action": "read",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "id": "public:read",
                "name": "Read Public Content",
                "description": "View public information",
                "resource": "public",
                "action": "read",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
        ]

        for permission in permissions:
            existing_permission = await self.get_record(
                "permissions", {"id": permission["id"]}
            )
            if not existing_permission:
                await self.insert_record("permissions", permission)

    async def _initialize_groups(self: DatabaseService) -> None:
        """Initialize default groups."""
        groups = [
            {
                "id": "admins",
                "name": "Administrators",
                "roles": ["admin"],
                "metadata": {"description": "System administrators with full access"},
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "id": "staff",
                "name": "Staff Members",
                "roles": ["manager", "user"],
                "metadata": {
                    "description": "Staff members with management and user access"
                },
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "id": "users",
                "name": "Regular Users",
                "roles": ["user"],
                "metadata": {"description": "Regular users with basic access"},
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "id": "guests",
                "name": "Guest Users",
                "roles": ["guest"],
                "metadata": {"description": "Guest users with limited access"},
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
        ]

        for group in groups:
            existing_group = await self.get_record("groups", {"id": group["id"]})
            if not existing_group:
                await self.insert_record("groups", group)

    async def _create_default_settings(self: DatabaseService) -> None:
        """Create default application settings."""
        default_settings = {
            "site_name": self.config.get("app_title", "One Conf"),
            "theme": "light",
            "maintenance_mode": False,
            "features": {
                "user_registration": True,
                "oauth_login": True,
                "rbac_enabled": True,
                "metrics_enabled": True,
                "tracing_enabled": True,
            },
            "security": {
                "password_min_length": 8,
                "password_require_special": True,
                "session_timeout": 3600,
                "max_login_attempts": 5,
            },
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        await self.insert_record("settings", default_settings)
