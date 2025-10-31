from __future__ import annotations
import json
from typing import Any

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError

from app.core.interfaces.database_interface import DatabaseInterface
from app.services.logger import Logger


class Redis(DatabaseInterface):
    """Redis client for caching, rate limiting, and session management.

    Features:
    - Connection pooling with configurable limits
    - Automatic retry and timeout handling
    - Health check support
    - JSON serialization/deserialization
    - Pattern-based operations
    """

    def __init__(
        self,
        host: str,
        port: int,
        db_name: str,
        logger: Logger,
        config: dict,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(host, port, db_name, logger, config, *args, **kwargs)
        self.password: str | None = (
            kwargs.get("password")
            if kwargs.get("password")
            else config.get("redis_password")
        )
        self.client: redis.Redis | None = None
        self.pool: ConnectionPool | None = None

    async def connect(self) -> None:
        """Connect to Redis with connection pooling."""
        self.logger.info("Connecting to Redis...")
        try:
            # Create connection pool with production settings
            self.pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=0,
                password=self.password,
                # Connection pool settings
                max_connections=self.config.get("redis_max_connections", 50),
                # Encoding settings
                decode_responses=self.config.get("redis_decode_responses", True),
                encoding="utf-8",
                # Connection settings
                socket_keepalive=self.config.get("redis_socket_keepalive", True),
                socket_keepalive_options={},
                socket_connect_timeout=5.0,
                socket_timeout=5.0,
                # Retry settings
                retry_on_timeout=self.config.get("redis_retry_on_timeout", True),
                retry_on_error=[ConnectionError, TimeoutError],
                # Health check
                health_check_interval=30,
            )

            # Create client from pool
            self.client = redis.Redis(connection_pool=self.pool)

            # Verify connection
            await self.client.ping()
            self.logger.info(f"Connected to Redis at {self.host}:{self.port}")

            await self.initialize_db()

        except ConnectionError as e:
            self.logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
        except TimeoutError as e:
            self.logger.error(f"Redis connection timeout: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error connecting to Redis: {str(e)}")
            raise

    async def close(self) -> None:
        """Close Redis connection and pool."""
        if self.client:
            self.logger.info("Closing Redis connection...")
            await self.client.close()

        if self.pool:
            await self.pool.disconnect()

        self.logger.info("Redis connection closed")

    async def execute_query(self, query: str, params: dict[str, Any]) -> Any:
        """Execute raw Redis command (use with caution)."""
        self.logger.warning("Raw query execution requested for Redis")
        raise NotImplementedError("Use specific Redis methods instead of raw queries")

    async def get_record(self, collection: str, filters: dict[str, Any]) -> dict | None:
        """Get record by key pattern (Redis doesn't have collections)."""
        # In Redis context, collection could be a key prefix
        key = f"{collection}:{filters.get('id', filters.get('key', '*'))}"
        return await self.get(key)

    async def initialize_db(self) -> None:
        """Initialize Redis (set initial keys if needed)."""
        self.logger.info("Redis initialized successfully")

    async def find_many(self, collection: str, filters: dict[str, Any]) -> list[dict]:
        """Find multiple records by pattern (Redis doesn't have collections)."""
        # In Redis context, we'll scan for keys matching the pattern
        pattern = f"{collection}:*"
        keys = await self.scan_keys(pattern)

        records = []
        for key in keys:
            value = await self.get(key)
            if value and isinstance(value, dict):
                # Check if the record matches the filters
                matches = True
                for filter_key, filter_value in filters.items():
                    if filter_key not in value or value[filter_key] != filter_value:
                        matches = False
                        break
                if matches:
                    records.append(value)

        return records

    async def insert_record(self, collection: str, data: dict[str, Any]) -> bool:
        """Insert a record (Redis doesn't have collections, uses key-value)."""
        # Generate a key for the record
        record_id = data.get("id", data.get("_id", "unknown"))
        key = f"{collection}:{record_id}"

        # Store the record
        result = await self.set(key, data)
        return result

    async def update_record(
        self, collection: str, filters: dict[str, Any], data: dict[str, Any]
    ) -> bool:
        """Update a record in Redis."""
        # Find the record first
        records = await self.find_many(collection, filters)
        if not records:
            return False

        # Update the first matching record
        record = records[0]
        record_id = record.get("id", record.get("_id", "unknown"))
        key = f"{collection}:{record_id}"

        # Merge the data
        updated_data = {**record, **data}

        # Store the updated record
        result = await self.set(key, updated_data)
        return result

    async def delete_record(self, collection: str, filters: dict[str, Any]) -> bool:
        """Delete a record from Redis."""
        # Find the record first
        records = await self.find_many(collection, filters)
        if not records:
            return False

        # Delete the first matching record
        record = records[0]
        record_id = record.get("id", record.get("_id", "unknown"))
        key = f"{collection}:{record_id}"

        # Delete the key
        result = await self.delete(key)
        return result > 0

    async def upsert_record(
        self, collection: str, filters: dict[str, Any], data: dict[str, Any]
    ) -> bool:
        """Upsert (update or insert) a record in Redis."""
        # Try to update first
        updated = await self.update_record(collection, filters, data)
        if updated:
            return True

        # If update failed, insert new record
        return await self.insert_record(collection, data)

    async def get(self, key: str) -> Any:
        """Get a value from Redis with automatic JSON deserialization."""
        if not self.client:
            raise RuntimeError("Redis connection not established")

        try:
            value = await self.client.get(key)
            if value:
                try:
                    # Try to deserialize JSON
                    return json.loads(value)
                except json.JSONDecodeError:
                    # Return as string if not JSON
                    return value
            return None
        except TimeoutError:
            self.logger.error(f"Timeout getting key: {key}")
            return None
        except Exception as e:
            self.logger.error(f"Error getting key {key}: {str(e)}")
            raise

    async def set(
        self,
        key: str,
        value: Any,
        expire: int | None = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """Set a value in Redis with optional expiration and conditions.

        Args:
            key: Redis key
            value: Value to store (will be JSON serialized if not string)
            expire: Expiration time in seconds
            nx: Only set if key doesn't exist
            xx: Only set if key exists

        """
        if not self.client:
            raise RuntimeError("Redis connection not established")

        try:
            # Serialize non-string values to JSON
            if not isinstance(value, (str, bytes, memoryview)):
                value = json.dumps(value)

            return await self.client.set(key, value, ex=expire, nx=nx, xx=xx)
        except Exception as e:
            self.logger.error(f"Error setting key {key}: {str(e)}")
            raise

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys from Redis."""
        if not self.client:
            raise RuntimeError("Redis connection not established")

        try:
            return await self.client.delete(*keys)
        except Exception as e:
            self.logger.error(f"Error deleting keys: {str(e)}")
            raise

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter in Redis."""
        if not self.client:
            raise RuntimeError("Redis connection not established")

        try:
            return await self.client.incr(key, amount)
        except Exception as e:
            self.logger.error(f"Error incrementing key {key}: {str(e)}")
            raise

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on a key."""
        if not self.client:
            raise RuntimeError("Redis connection not established")

        try:
            return await self.client.expire(key, seconds)
        except Exception as e:
            self.logger.error(f"Error setting expiration on key {key}: {str(e)}")
            raise

    async def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        if not self.client:
            raise RuntimeError("Redis connection not established")

        try:
            return await self.client.exists(*keys)
        except Exception as e:
            self.logger.error(f"Error checking existence of keys: {str(e)}")
            raise

    async def scan_keys(self, pattern: str = "*", count: int = 100) -> list[str]:
        """Scan for keys matching a pattern."""
        if not self.client:
            raise RuntimeError("Redis connection not established")

        try:
            keys = []
            async for key in self.client.scan_iter(match=pattern, count=count):
                keys.append(key)
            return keys
        except Exception as e:
            self.logger.error(f"Error scanning keys with pattern {pattern}: {str(e)}")
            raise

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        keys = await self.scan_keys(pattern)
        if keys:
            return await self.delete(*keys)
        return 0

    async def mget(self, keys: list[str]) -> list[Any]:
        """Get multiple values at once."""
        if not self.client:
            raise RuntimeError("Redis connection not established")

        try:
            values = await self.client.mget(keys)
            # Deserialize JSON values
            result = []
            for value in values:
                if value:
                    try:
                        result.append(json.loads(value))
                    except json.JSONDecodeError:
                        result.append(value)
                else:
                    result.append(None)
            return result
        except Exception as e:
            self.logger.error(f"Error in mget: {str(e)}")
            raise

    async def mset(self, mapping: dict[str, Any]) -> bool:
        """Set multiple key-value pairs at once."""
        if not self.client:
            raise RuntimeError("Redis connection not established")

        try:
            # Serialize values
            serialized = {}
            for key, value in mapping.items():
                if not isinstance(value, (str, bytes, memoryview)):
                    serialized[key] = json.dumps(value)
                else:
                    serialized[key] = value

            return await self.client.mset(serialized)
        except Exception as e:
            self.logger.error(f"Error in mset: {str(e)}")
            raise

    async def health_check(self) -> bool:
        """Check if Redis connection is healthy."""
        try:
            await self.client.ping()
            return True
        except Exception as e:
            self.logger.error(f"Redis health check failed: {str(e)}")
            return False

    async def get_pool_stats(self) -> dict:
        """Get connection pool statistics."""
        if not self.pool:
            return {}

        return {
            "created_connections": self.pool.created_connections,
            "available_connections": len(self.pool._available_connections),
            "in_use_connections": len(self.pool._in_use_connections),
            "max_connections": self.pool.max_connections,
        }
