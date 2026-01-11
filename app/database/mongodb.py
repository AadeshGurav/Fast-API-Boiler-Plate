from __future__ import annotations

import urllib.parse
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.core.interfaces.database_interface import DatabaseInterface


class MongoDB(DatabaseInterface):
    """MongoDB client using Motor for async operations with connection pooling."""

    async def connect(self) -> None:
        """Connect to MongoDB with production-ready settings."""
        self.logger.info("Connecting to MongoDB...")
        try:
            # Create connection string with authentication if credentials exist
            # Get username and password from config or use default None
            username = self.config.get("mongo_username")
            password = self.config.get("mongo_password")
            auth_source = self.config.get("mongo_auth_source", "admin")

            # Build base connection string
            if username and password:
                encoded_username = urllib.parse.quote_plus(username)
                encoded_password = urllib.parse.quote_plus(password)
                connection_string = (
                    f"mongodb://{encoded_username}:{encoded_password}"
                    f"@{self.host}:{self.port}/{self.db_name}"
                    f"?authSource={auth_source}"
                )
            else:
                connection_string = f"mongodb://{self.host}:{self.port}/{self.db_name}"

            # Create client with connection pooling configuration
            self.client = AsyncIOMotorClient(
                connection_string,
                # Connection pool settings
                maxPoolSize=self.config.get("mongo_pool_size", 100),
                minPoolSize=self.config.get("mongo_min_pool_size", 10),
                maxIdleTimeMS=self.config.get("mongo_max_idle_time_ms", 30000),
                waitQueueTimeoutMS=self.config.get("mongo_wait_queue_timeout_ms", 5000),
                # Timeout settings
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000,
                # Performance settings
                directConnection=self.config.get("mongo_direct_connection", False),
                retryWrites=True,
                retryReads=True,
                # Monitoring
                appname=self.config.get("app_title", "fastapi-app"),
            )

            self.db = self.client[self.db_name]

            # Verify connection with ping
            await self.client.admin.command("ping")
            self.logger.info(f"Connected to MongoDB at {self.host}:{self.port}")

            # Initialize the database after successful connection
            await self.initialize_db()

        except ServerSelectionTimeoutError as e:
            self.logger.error(f"MongoDB connection timeout: {str(e)}")
            raise
        except ConnectionFailure as e:
            self.logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error connecting to MongoDB: {str(e)}")
            raise

    async def initialize_db(self) -> None:
        """Initialize the database with required collections and indexes."""
        try:
            self.logger.info("Initializing MongoDB database structure...")

            # Create necessary collections if they don't exist
            collections = await self.db.list_collection_names()
            required_collections = [
                "users",
                "sessions",
                "roles",
                "permissions",
                "groups",
                "temporary_permissions",
                "oauth_accounts",
                "settings",
                "files",
            ]

            for collection in required_collections:
                if collection not in collections:
                    await self.db.create_collection(collection)
                    self.logger.info(f"Created collection: {collection}")

            # Create indexes for better performance
            await self._create_indexes()

            self.logger.info("MongoDB database structure initialization completed")
        except Exception as e:
            self.logger.error(
                f"MongoDB database structure initialization failed: {str(e)}"
            )
            raise

    async def _create_indexes(self) -> None:
        """Create database indexes for optimal performance."""
        try:
            # User collection indexes
            await self.db.users.create_index("username", unique=True)
            await self.db.users.create_index("email", sparse=True)
            await self.db.users.create_index([("created_at", -1)])

            # Session collection indexes
            await self.db.sessions.create_index("user_id")
            await self.db.sessions.create_index("expires_at")
            await self.db.sessions.create_index("revoked_at", sparse=True)

            # Role collection indexes
            await self.db.roles.create_index("id", unique=True)
            await self.db.roles.create_index("name", unique=True)

            # Permission collection indexes
            await self.db.permissions.create_index("id", unique=True)
            await self.db.permissions.create_index("name", unique=True)

            # Group collection indexes
            await self.db.groups.create_index("id", unique=True)
            await self.db.groups.create_index("name", unique=True)

            # Temporary permissions indexes
            await self.db.temporary_permissions.create_index("entity_id")
            await self.db.temporary_permissions.create_index("end_time")

            # OAuth accounts indexes
            await self.db.oauth_accounts.create_index(
                [("user_id", 1), ("provider", 1)], unique=True
            )

            # Settings collection indexes
            await self.db.settings.create_index("site_name", unique=True)

            # Files collection indexes
            await self.db.files.create_index("file_id", unique=True)
            await self.db.files.create_index("user_id")
            await self.db.files.create_index("hash")
            await self.db.files.create_index([("created_at", -1)])
            await self.db.files.create_index("tags")
            await self.db.files.create_index("deleted_at", sparse=True)

            self.logger.info("MongoDB indexes created successfully")
        except Exception as e:
            self.logger.error(f"MongoDB index creation failed: {str(e)}")
            raise

    async def close(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.logger.info("Closing MongoDB connection...")
            self.client.close()
            self.logger.info("MongoDB connection closed")

    def get_collection(self, collection_name: str) -> AsyncIOMotorCollection:
        """Get a collection from the database."""
        if self.db is None:
            raise RuntimeError("MongoDB connection not established")
        return self.db[collection_name]

    def _normalize_filters(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Convert application filters to MongoDB format.

        Args:
        ----
            filters: Application filter dictionary.

        Returns:
        -------
            MongoDB-compatible filter dictionary.

        """
        normalized = filters.copy()
        if "id" in normalized and "_id" not in normalized:
            id_value = normalized["id"]
            if isinstance(id_value, str) and len(id_value) == 24:
                try:
                    ObjectId(id_value)
                    normalized["_id"] = ObjectId(normalized.pop("id"))
                except (ValueError, TypeError):
                    pass
        return normalized

    def _normalize_record(
        self: MongoDB, record: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Convert MongoDB record to application format.

        Args:
        ----
            record: MongoDB record dictionary.

        Returns:
        -------
            Application-compatible record dictionary.

        """
        from app.services.data.data_service import _normalize_record

        return _normalize_record(record)

    async def execute_query(self, query: str, params: dict[str, Any]) -> Any:
        """Execute a raw query (not recommended for MongoDB)."""
        self.logger.warning(
            "Raw query execution requested for MongoDB - consider using collection methods instead"
        )
        raise NotImplementedError(
            "Use collection-specific methods for MongoDB operations"
        )

    async def get_record(self, collection: str, filters: dict[str, Any]) -> dict | None:
        """Fetch a single record with timeout."""
        try:
            coll = self.get_collection(collection)
            normalized_filters = self._normalize_filters(filters)
            result = await coll.find_one(normalized_filters, max_time_ms=5000)
            return self._normalize_record(result)
        except Exception as e:
            self.logger.error(f"Error fetching record from {collection}: {str(e)}")
            raise

    async def find_many(self, collection: str, filters: dict[str, Any]) -> list[dict]:
        """Fetch multiple records with timeout."""
        try:
            coll = self.get_collection(collection)
            normalized_filters = self._normalize_filters(filters)
            cursor = coll.find(normalized_filters, max_time_ms=5000)
            result = await cursor.to_list(length=None)
            return [self._normalize_record(record) for record in result]
        except Exception as e:
            self.logger.error(f"Error fetching records from {collection}: {str(e)}")
            raise

    async def insert_record(self, collection: str, data: dict[str, Any]) -> bool:
        """Insert a new record into the collection."""
        try:
            coll = self.get_collection(collection)
            result = await coll.insert_one(data)
            self.logger.debug(
                f"Inserted record into {collection} with ID: {result.inserted_id}"
            )
            return result.inserted_id is not None
        except Exception as e:
            self.logger.error(f"Error inserting record into {collection}: {str(e)}")
            raise

    async def update_record(
        self, collection: str, filters: dict[str, Any], data: dict[str, Any]
    ) -> bool:
        """Update records in the collection."""
        try:
            coll = self.get_collection(collection)
            normalized_filters = self._normalize_filters(filters)
            result = await coll.update_one(normalized_filters, {"$set": data})
            self.logger.debug(
                f"Updated {result.modified_count} record(s) in {collection}"
            )
            return result.modified_count > 0
        except Exception as e:
            self.logger.error(f"Error updating record in {collection}: {str(e)}")
            raise

    async def delete_record(self, collection: str, filters: dict[str, Any]) -> bool:
        """Delete records from the collection."""
        try:
            coll = self.get_collection(collection)
            normalized_filters = self._normalize_filters(filters)
            result = await coll.delete_one(normalized_filters)
            self.logger.debug(
                f"Deleted {result.deleted_count} record(s) from {collection}"
            )
            return result.deleted_count > 0
        except Exception as e:
            self.logger.error(f"Error deleting record from {collection}: {str(e)}")
            raise

    async def upsert_record(
        self, collection: str, filters: dict[str, Any], data: dict[str, Any]
    ) -> bool:
        """Upsert (update or insert) a record in the collection."""
        try:
            coll = self.get_collection(collection)
            normalized_filters = self._normalize_filters(filters)
            result = await coll.update_one(
                normalized_filters, {"$set": data}, upsert=True
            )
            self.logger.debug(
                f"Upserted record in {collection}: "
                f"matched={result.matched_count}, "
                f"modified={result.modified_count}, "
                f"upserted_id={result.upserted_id}"
            )
            return True
        except Exception as e:
            self.logger.error(f"Error upserting record in {collection}: {str(e)}")
            raise

    async def health_check(self) -> bool:
        """Check if MongoDB connection is healthy."""
        try:
            # Ping with timeout
            await self.client.admin.command("ping", maxTimeMS=1000)
            return True
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"MongoDB health check failed: {str(e)}")
            return False
