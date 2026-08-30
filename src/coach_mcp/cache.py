"""Zero-dependency async-safe TTL cache."""

import asyncio
import time
from typing import Any


class TTLCache:
    """In-memory cache with per-key time-to-live expiration.

    The cache is safe for concurrent asyncio tasks. Expiration is checked on
    every read using ``time.monotonic()``. A value with a negative TTL never
    expires.
    """

    def __init__(self, default_ttl: int = 300) -> None:
        self.default_ttl = default_ttl
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        """Return the cached value or ``None`` if missing or expired."""
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None

            value, expires_at = entry
            if expires_at >= 0 and time.monotonic() > expires_at:
                del self._store[key]
                return None

            return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store ``value`` under ``key`` with an optional custom TTL."""
        effective_ttl = ttl if ttl is not None else self.default_ttl
        expires_at = -1.0 if effective_ttl < 0 else time.monotonic() + effective_ttl

        async with self._lock:
            self._store[key] = (value, expires_at)

    async def clear(self) -> None:
        """Remove all cached entries."""
        async with self._lock:
            self._store.clear()

    async def invalidate(self, key: str) -> None:
        """Remove a single cached entry if it exists."""
        async with self._lock:
            self._store.pop(key, None)

    async def invalidate_prefix(self, prefix: str) -> None:
        """Remove all cached entries whose keys start with ``prefix``."""
        async with self._lock:
            for key in list(self._store):
                if key.startswith(prefix):
                    self._store.pop(key, None)
