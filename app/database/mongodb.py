from __future__ import annotations

import urllib.parse
from datetime import UTC
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo import ReturnDocument
from pymongo.errors import (
    ConnectionFailure,
    OperationFailure,
    ServerSelectionTimeoutError,
)

from app.core.interfaces.database_interface import DatabaseInterface

# IndexOptionsConflict / IndexKeySpecsConflict
INDEX_CONFLICT_CODES = {85, 86}
# IndexNotFound / NamespaceNotFound (collection not created yet)
INDEX_NOT_FOUND_CODES = {26, 27}
AUTH_FAILED = 18
# Safety net for queries that forget to paginate.
MAX_UNPAGED_RESULTS = 10_000


class MongoDB(DatabaseInterface):
    """MongoDB backend (settings: ``mongo_host/port/username/password/auth_source``,
    ``app_database``)."""

    def __init__(self, config, logger) -> None:
        super().__init__(config, logger)
        self.host = config["mongo_host"]
        self.port = config["mongo_port"]
        self.db_name = config["app_database"]
        self.db = None

    async def connect(self) -> None:
        """Connect to MongoDB with production-ready settings."""
        self.logger.info("Connecting to MongoDB...")

        try:
            # 1. Prepare configuration
            uri = self._build_connection_uri()
            options = self._get_client_options()

            # 2. Initialize Client
            self.client = AsyncIOMotorClient(uri, **options)
            self.db = self.client[self.db_name]

            # 3. Verify Connection
            await self.client.admin.command("ping")
            self.logger.info(f"Connected to MongoDB at {self.host}:{self.port}")

            # 4. Run App-specific Init
            await self.initialize_db()

        except (ServerSelectionTimeoutError, ConnectionFailure) as e:
            self.logger.error(f"MongoDB connection failed: {e}")
            raise
        except OperationFailure as e:
            if e.code == AUTH_FAILED:
                self.logger.error(
                    "MongoDB rejected the credentials (mongo_username/mongo_password). If you "
                    "regenerated .env while a Docker volume from an earlier run exists, the "
                    "old password is still stored there: run `make reset-data` (deletes the "
                    "local dev databases)."
                )
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error connecting to MongoDB: {e}")
            raise

    def _build_connection_uri(self) -> str:
        """Construct the MongoDB connection URI safely handling auth."""
        # 'or None' treats empty strings as None
        username = self.config["mongo_username"] or None
        password = self.config["mongo_password"] or None
        auth_src = self.config["mongo_auth_source"] or "admin"

        self.logger.debug(
            f"MongoDB Config - host: {self.host}, port: {self.port}, "
            f"user: {username}, auth_src: {auth_src}, has_pwd: {bool(password)}"
        )

        base_uri = f"mongodb://{self.host}:{self.port}/{self.db_name}"

        if not (username and password):
            return base_uri

        # Encode credentials safely
        user_enc = urllib.parse.quote_plus(username)
        pass_enc = urllib.parse.quote_plus(password)
        return f"mongodb://{user_enc}:{pass_enc}@{self.host}:{self.port}/{self.db_name}?authSource={auth_src}"

    def _get_client_options(self) -> dict:
        """Centralize MongoDB client configuration parameters."""
        return {
            # Pool Settings
            "maxPoolSize": self.config["mongo_pool_size"],
            "minPoolSize": self.config["mongo_min_pool_size"],
            "maxIdleTimeMS": self.config["mongo_max_idle_time_ms"],
            "waitQueueTimeoutMS": self.config["mongo_wait_queue_timeout_ms"],
            # Timeouts
            "serverSelectionTimeoutMS": self.config["mongo_timeout_ms"],
            "connectTimeoutMS": self.config["mongo_timeout_ms"],
            "socketTimeoutMS": self.config["mongo_timeout_ms"],
            # Operational
            "directConnection": self.config["mongo_direct_connection"],
            "retryWrites": True,
            "retryReads": True,
            # PyMongo returns naive datetimes by default; every expiry check in the app
            # compares against timezone-aware UTC and would raise TypeError.
            "tz_aware": True,
            "tzinfo": UTC,
            "appname": self.config["app_title"],
        }

    async def initialize_db(self) -> None:
        """No backend-level setup: MongoDB creates collections on first write.

        Which collections and indexes exist is the data layer's decision; it
        declares them through ``ensure_indexes``.
        """
        self.logger.info("MongoDB ready")

    async def ensure_indexes(self, indexes: dict[str, list[dict[str, Any]]]) -> None:
        """Create the declared indexes (idempotent).

        Args:
        ----
            indexes: ``{collection: [{"keys": [(field, direction)], **options}]}``.

        """
        try:
            for collection, specs in indexes.items():
                for spec in specs:
                    await self._ensure_index(collection, spec)
            self.logger.info("MongoDB indexes ensured")
        except Exception as e:
            self.logger.error(f"MongoDB index creation failed: {e!s}")
            raise

    async def drop_indexes(self, indexes: dict[str, list[str]]) -> None:
        """Drop the named indexes; absent ones (or collections) are ignored."""
        for collection, names in indexes.items():
            for name in names:
                try:
                    await self.get_collection(collection).drop_index(name)
                    self.logger.info(f"Dropped index {collection}.{name}")
                except OperationFailure as e:
                    if e.code not in INDEX_NOT_FOUND_CODES:
                        raise

    async def _ensure_index(self, collection: str, spec: dict[str, Any]) -> None:
        """Create one index; if an index with the same keys but different options
        exists (e.g. a plain index later declared as TTL), replace it."""
        coll = self.get_collection(collection)
        options = {k: v for k, v in spec.items() if k != "keys"}
        try:
            await coll.create_index(spec["keys"], **options)
        except OperationFailure as e:
            if e.code not in INDEX_CONFLICT_CODES:
                raise
            name = "_".join(f"{field}_{direction}" for field, direction in spec["keys"])
            self.logger.warning(f"Replacing conflicting index {collection}.{name}")
            await coll.drop_index(name)
            await coll.create_index(spec["keys"], **options)

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

    def _normalize_record(self: MongoDB, record: dict[str, Any] | None) -> dict[str, Any] | None:
        """Expose Mongo's ``_id`` as a string ``id``; nothing domain-specific.

        Args:
        ----
            record: MongoDB record dictionary.

        Returns:
        -------
            Record with ``id`` instead of ``_id``, or None.

        """
        if not record:
            return None
        normalized = record.copy()
        if "_id" in normalized:
            # A record's own business ``id`` (uuid, role slug) must win over the
            # surrogate Mongo key, otherwise every read silently rewrites it.
            normalized.setdefault("id", str(normalized["_id"]))
            del normalized["_id"]
        return normalized

    async def get_record(self, collection: str, filters: dict[str, Any]) -> dict | None:
        """Fetch a single record with timeout."""
        try:
            coll = self.get_collection(collection)
            normalized_filters = self._normalize_filters(filters)
            result = await coll.find_one(normalized_filters, max_time_ms=5000)
            return self._normalize_record(result)
        except Exception as e:
            self.logger.error(f"Error fetching record from {collection}: {e!s}")
            raise

    async def find_many(
        self,
        collection: str,
        filters: dict[str, Any],
        *,
        limit: int | None = None,
        skip: int = 0,
        sort: list[tuple[str, int]] | None = None,
    ) -> list[dict]:
        """Fetch matching records (capped at ``MAX_UNPAGED_RESULTS`` without a ``limit``)."""
        try:
            cursor = self.get_collection(collection).find(
                self._normalize_filters(filters), max_time_ms=5000
            )
            if sort:
                cursor = cursor.sort(sort)
            cursor = cursor.skip(skip).limit(limit or MAX_UNPAGED_RESULTS)
            result = await cursor.to_list(length=None)
            if limit is None and len(result) == MAX_UNPAGED_RESULTS:
                self.logger.warning(
                    f"Unpaged query on {collection} hit the {MAX_UNPAGED_RESULTS}-record cap; "
                    "page it with limit/skip"
                )
            return [self._normalize_record(record) for record in result]
        except Exception as e:
            self.logger.error(f"Error fetching records from {collection}: {e!s}")
            raise

    async def count(self, collection: str, filters: dict[str, Any]) -> int:
        """Number of matching records."""
        return await self.get_collection(collection).count_documents(
            self._normalize_filters(filters), maxTimeMS=5000
        )

    async def insert_record(self, collection: str, data: dict[str, Any]) -> bool:
        """Insert a new record into the collection."""
        try:
            coll = self.get_collection(collection)
            result = await coll.insert_one(data)
            self.logger.debug(f"Inserted record into {collection} with ID: {result.inserted_id}")
            return result.inserted_id is not None
        except Exception as e:
            self.logger.error(f"Error inserting record into {collection}: {e!s}")
            raise

    async def update_record(
        self, collection: str, filters: dict[str, Any], data: dict[str, Any]
    ) -> bool:
        """Update records in the collection."""
        try:
            coll = self.get_collection(collection)
            normalized_filters = self._normalize_filters(filters)
            result = await coll.update_one(normalized_filters, {"$set": data})
            self.logger.debug(f"Updated {result.modified_count} record(s) in {collection}")
            return result.matched_count > 0
        except Exception as e:
            self.logger.error(f"Error updating record in {collection}: {e!s}")
            raise

    async def update_many(
        self, collection: str, filters: dict[str, Any], data: dict[str, Any]
    ) -> int:
        """``$set`` ``data`` on every matching record."""
        result = await self.get_collection(collection).update_many(
            self._normalize_filters(filters), {"$set": data}
        )
        return result.matched_count

    async def delete_record(self, collection: str, filters: dict[str, Any]) -> bool:
        """Delete records from the collection."""
        try:
            coll = self.get_collection(collection)
            normalized_filters = self._normalize_filters(filters)
            result = await coll.delete_one(normalized_filters)
            self.logger.debug(f"Deleted {result.deleted_count} record(s) from {collection}")
            return result.deleted_count > 0
        except Exception as e:
            self.logger.error(f"Error deleting record from {collection}: {e!s}")
            raise

    async def increment_field(
        self, collection: str, filters: dict[str, Any], field: str, amount: int = 1
    ) -> int | None:
        """Atomically ``$inc`` a field and return the new value (None if no match)."""
        try:
            coll = self.get_collection(collection)
            updated = await coll.find_one_and_update(
                self._normalize_filters(filters),
                {"$inc": {field: amount}},
                projection={field: 1},
                return_document=ReturnDocument.AFTER,
            )
            return None if updated is None else updated.get(field)
        except Exception as e:
            self.logger.error(f"Error incrementing {field} in {collection}: {e!s}")
            raise

    async def upsert_record(
        self, collection: str, filters: dict[str, Any], data: dict[str, Any]
    ) -> bool:
        """Upsert (update or insert) a record in the collection."""
        try:
            coll = self.get_collection(collection)
            normalized_filters = self._normalize_filters(filters)
            result = await coll.update_one(normalized_filters, {"$set": data}, upsert=True)
            self.logger.debug(
                f"Upserted record in {collection}: "
                f"matched={result.matched_count}, "
                f"modified={result.modified_count}, "
                f"upserted_id={result.upserted_id}"
            )
            return True
        except Exception as e:
            self.logger.error(f"Error upserting record in {collection}: {e!s}")
            raise

    async def health_check(self) -> bool:
        """Check if MongoDB connection is healthy."""
        try:
            # Ping with timeout
            await self.client.admin.command("ping", maxTimeMS=1000)
            return True
        except Exception as e:
            self.logger.error(f"MongoDB health check failed: {e!s}")
            return False
