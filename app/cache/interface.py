"""The contract a cache backend implements. Bring your own by implementing this class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.logger import Logger
    from config import Config


class CacheUnavailableError(RuntimeError):
    """The cache could not be reached, and the operation has no safe fallback."""


@dataclass(frozen=True)
class RateDecision:
    """Outcome of counting one request against a limit."""

    allowed: bool
    current: int  # requests counted in the window, including this one if allowed
    retry_after: int | None  # seconds until a slot frees up, when not allowed


class CacheInterface(ABC):
    """A key-value cache with expiry, prefix deletion and atomic rate counting.

    Values are JSON-serialisable; ``get`` returns what ``set`` stored. Constructed with
    ``(config, logger)``; read your own settings from ``config``.
    """

    def __init__(self, config: Config, logger: Logger) -> None:
        self.config = config
        self.logger = logger

    @abstractmethod
    async def connect(self) -> None:
        """Open connections; raise if the cache is unreachable."""

    @abstractmethod
    async def close(self) -> None:
        """Release connections."""

    @abstractmethod
    async def health_check(self) -> bool:
        """True if the cache currently answers requests."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Whether ``connect`` has succeeded."""

    @abstractmethod
    async def get(self, key: str) -> Any:
        """The stored value, or None if missing/expired."""

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Store ``value`` for ``ttl`` seconds (no expiry if None)."""

    @abstractmethod
    async def add(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Store ``value`` only if ``key`` is absent; True if this call stored it (atomic)."""

    @abstractmethod
    async def delete(self, *keys: str) -> int:
        """Delete keys; returns how many existed."""

    @abstractmethod
    async def delete_prefix(self, prefix: str) -> int:
        """Delete every key starting with ``prefix``; returns how many."""

    @abstractmethod
    async def hit(self, key: str, limit: int, window: int, *, sliding: bool = True) -> RateDecision:
        """Atomically count one request in a ``window``-second window against ``limit``.

        Must be atomic: concurrent callers may not both take the last slot.
        """
