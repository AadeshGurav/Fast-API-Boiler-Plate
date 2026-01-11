from __future__ import annotations

from enum import Enum


class CachePolicy(str, Enum):
    """Cache policy enum for data operations.

    Defines how data operations should interact with cache and database:
    - AUTO: Smart caching (read: cache->db; write/delete: db then cache)
    - CACHE_ONLY: Operate on cache only
    - DB_ONLY: Operate on database only
    """

    AUTO = "auto"  # read: cache->db; write/delete: db then cache
    CACHE_ONLY = "cache"  # operate on cache only
    DB_ONLY = "db"  # operate on db only


__all__ = ["CachePolicy"]
