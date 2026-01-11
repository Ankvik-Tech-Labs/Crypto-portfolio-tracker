"""TTL-based caching for RPC responses."""

import hashlib
import json
import time
from typing import Any


class CacheEntry:
    """
    Cache entry with TTL support.

    Parameters
    ----------
    value : Any
        Cached value
    ttl : int
        Time-to-live in seconds
    created_at : float | None
        Creation timestamp. Uses current time if None.

    """

    def __init__(self, value: Any, ttl: int, created_at: float | None = None) -> None:
        self.value = value
        self.ttl = ttl
        self.created_at = created_at or time.time()

    def is_expired(self) -> bool:
        """
        Check if cache entry has expired.

        Returns
        -------
        bool
            True if expired, False otherwise

        """
        return (time.time() - self.created_at) > self.ttl


class RPCCache:
    """
    In-memory cache for RPC responses with TTL.

    Parameters
    ----------
    default_ttl : int
        Default time-to-live in seconds for cache entries

    """

    def __init__(self, default_ttl: int = 300) -> None:
        self.default_ttl = default_ttl
        self._cache: dict[str, CacheEntry] = {}

    def _make_key(self, method: str, params: list[Any]) -> str:
        """
        Generate cache key from method and parameters.

        Parameters
        ----------
        method : str
            RPC method name
        params : list[Any]
            Method parameters

        Returns
        -------
        str
            Cache key

        """
        # Create a deterministic string representation
        key_data = {"method": method, "params": params}
        key_str = json.dumps(key_data, sort_keys=True)
        # Hash for consistent key length
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(self, method: str, params: list[Any]) -> Any | None:
        """
        Get cached value if it exists and hasn't expired.

        Parameters
        ----------
        method : str
            RPC method name
        params : list[Any]
            Method parameters

        Returns
        -------
        Any | None
            Cached value if found and valid, None otherwise

        """
        key = self._make_key(method, params)
        entry = self._cache.get(key)

        if entry is None:
            return None

        if entry.is_expired():
            # Clean up expired entry
            del self._cache[key]
            return None

        return entry.value

    def set(self, method: str, params: list[Any], value: Any, ttl: int | None = None) -> None:
        """
        Store value in cache with TTL.

        Parameters
        ----------
        method : str
            RPC method name
        params : list[Any]
            Method parameters
        value : Any
            Value to cache
        ttl : int | None
            Time-to-live in seconds. Uses default_ttl if None.

        """
        key = self._make_key(method, params)
        ttl = ttl or self.default_ttl
        self._cache[key] = CacheEntry(value, ttl)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.

        Returns
        -------
        int
            Number of entries removed

        """
        expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)
