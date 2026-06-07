import time
from typing import Any, Dict, Optional, Tuple

class SimpleCache:
    def __init__(self, default_ttl: int = 30):
        self.default_ttl = default_ttl
        self._cache: Dict[str, Tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        """Retrieves a cached value if it exists and has not expired."""
        if key not in self._cache:
            return None
        val, expiry = self._cache[key]
        if time.time() > expiry:
            del self._cache[key]
            return None
        return val

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Stores a value in cache with a TTL (defaults to default_ttl)."""
        duration = ttl if ttl is not None else self.default_ttl
        expiry = time.time() + duration
        self._cache[key] = (value, expiry)

    def clear(self) -> None:
        """Clears all cached items."""
        self._cache.clear()
