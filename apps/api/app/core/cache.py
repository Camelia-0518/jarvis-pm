"""Cache layer implementation with Redis support"""

import json
import hashlib
import logging
import pickle
from typing import Any, Optional, Callable, Union
from functools import wraps
from datetime import datetime, timedelta
import asyncio

from app.core.config import settings

logger = logging.getLogger(__name__)

# Try to import redis, fallback to in-memory cache if not available
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class CacheManager:
    """Cache manager with Redis and in-memory fallback"""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis: Optional[Any] = None
        self._local_cache: dict = {}
        self._local_ttl: dict = {}
        self._lock = asyncio.Lock()

    async def connect(self):
        """Connect to Redis if available"""
        if REDIS_AVAILABLE and self.redis_url:
            try:
                self._redis = redis.from_url(self.redis_url, decode_responses=True)
                await self._redis.ping()
                logger.info(f"✅ Redis cache connected: {self.redis_url}")
            except Exception as e:
                logger.warning(f"⚠️ Redis connection failed: {e}, falling back to in-memory cache")
                self._redis = None
        else:
            logger.info("ℹ️ Using in-memory cache")

    async def disconnect(self):
        """Disconnect from Redis"""
        if self._redis:
            await self._redis.close()
            self._redis = None

    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = f"{prefix}:{str(args)}:{str(kwargs)}"
        return f"{prefix}:{hashlib.md5(key_data.encode()).hexdigest()}"

    def _serialize(self, value: Any) -> str:
        """Serialize value to string"""
        if isinstance(value, (str, int, float, bool)):
            return json.dumps({"_type": "primitive", "value": value})
        return json.dumps(value, default=str)

    def _deserialize(self, value: str) -> Any:
        """Deserialize value from string"""
        try:
            data = json.loads(value)
            if isinstance(data, dict) and data.get("_type") == "primitive":
                return data["value"]
            return data
        except json.JSONDecodeError:
            return value

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        # Try Redis first
        if self._redis:
            try:
                value = await self._redis.get(key)
                if value:
                    return self._deserialize(value)
            except Exception:
                pass

        # Fallback to local cache
        async with self._lock:
            if key in self._local_cache:
                expiry = self._local_ttl.get(key)
                if expiry and expiry > datetime.utcnow():
                    return self._local_cache[key]
                else:
                    # Expired, remove
                    del self._local_cache[key]
                    if key in self._local_ttl:
                        del self._local_ttl[key]

        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,
        nx: bool = False
    ) -> bool:
        """Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            nx: Only set if key doesn't exist
        """
        serialized = self._serialize(value)

        # Try Redis first
        if self._redis:
            try:
                if nx:
                    result = await self._redis.setnx(key, serialized)
                    if result:
                        await self._redis.expire(key, ttl)
                    return bool(result)
                else:
                    await self._redis.setex(key, ttl, serialized)
                    return True
            except Exception as e:
                logger.error(f"Redis set error: {e}")

        # Fallback to local cache
        async with self._lock:
            if nx and key in self._local_cache:
                return False

            self._local_cache[key] = value
            self._local_ttl[key] = datetime.utcnow() + timedelta(seconds=ttl)
            return True

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        result = False

        if self._redis:
            try:
                result = await self._redis.delete(key) > 0
            except Exception:
                pass

        async with self._lock:
            if key in self._local_cache:
                del self._local_cache[key]
                if key in self._local_ttl:
                    del self._local_ttl[key]
                result = True

        return result

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if self._redis:
            try:
                return await self._redis.exists(key) > 0
            except Exception:
                pass

        async with self._lock:
            if key in self._local_cache:
                expiry = self._local_ttl.get(key)
                if expiry and expiry > datetime.utcnow():
                    return True
        return False

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter in cache"""
        if self._redis:
            try:
                return await self._redis.incrby(key, amount)
            except Exception:
                pass

        async with self._lock:
            current = self._local_cache.get(key, 0)
            if isinstance(current, int):
                self._local_cache[key] = current + amount
                return self._local_cache[key]
            return 0

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on key"""
        if self._redis:
            try:
                return await self._redis.expire(key, ttl)
            except Exception:
                pass

        async with self._lock:
            if key in self._local_cache:
                self._local_ttl[key] = datetime.utcnow() + timedelta(seconds=ttl)
                return True
        return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        count = 0

        if self._redis:
            try:
                keys = await self._redis.keys(pattern)
                if keys:
                    count = await self._redis.delete(*keys)
            except Exception:
                pass

        # Local cache - simple substring match
        async with self._lock:
            keys_to_delete = [k for k in self._local_cache.keys() if pattern.replace("*", "") in k]
            for key in keys_to_delete:
                del self._local_cache[key]
                if key in self._local_ttl:
                    del self._local_ttl[key]
            count += len(keys_to_delete)

        return count

    def cached(
        self,
        ttl: int = 3600,
        key_prefix: str = "cache",
        key_builder: Optional[Callable] = None,
        unless: Optional[Callable] = None
    ):
        """Decorator for caching function results

        Args:
            ttl: Cache time-to-live in seconds
            key_prefix: Prefix for cache key
            key_builder: Custom key builder function
            unless: Function to determine if result should not be cached
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Check unless condition
                if unless and unless(*args, **kwargs):
                    return await func(*args, **kwargs)

                # Generate cache key
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    cache_key = self._generate_key(key_prefix, *args, **kwargs)

                # Try to get from cache
                cached_value = await self.get(cache_key)
                if cached_value is not None:
                    return cached_value

                # Execute function
                result = await func(*args, **kwargs)

                # Cache result
                await self.set(cache_key, result, ttl)

                return result

            # Add cache management methods to wrapper
            wrapper.cache_key = lambda *args, **kwargs: (
                key_builder(*args, **kwargs) if key_builder
                else self._generate_key(key_prefix, *args, **kwargs)
            )
            wrapper.cache_delete = lambda *args, **kwargs: self.delete(
                key_builder(*args, **kwargs) if key_builder
                else self._generate_key(key_prefix, *args, **kwargs)
            )
            wrapper.cache_clear = lambda: self.clear_pattern(f"{key_prefix}:*")

            return wrapper
        return decorator

    async def health_check(self) -> dict:
        """Check cache health"""
        if self._redis:
            try:
                info = await self._redis.info()
                return {
                    "status": "connected",
                    "type": "redis",
                    "version": info.get("redis_version", "unknown"),
                    "used_memory": info.get("used_memory_human", "unknown"),
                    "connected_clients": info.get("connected_clients", 0)
                }
            except Exception as e:
                return {
                    "status": "error",
                    "type": "redis",
                    "error": str(e)
                }

        return {
            "status": "active",
            "type": "memory",
            "keys": len(self._local_cache)
        }


# Global cache manager instance
cache_manager = CacheManager()


# ============== Helper Functions ==============

async def init_cache():
    """Initialize cache connection"""
    await cache_manager.connect()


async def close_cache():
    """Close cache connection"""
    await cache_manager.disconnect()


async def cached(
    ttl: int = 3600,
    key_prefix: str = "cache",
    key_builder: Optional[Callable] = None,
    unless: Optional[Callable] = None
):
    """Shortcut decorator using global cache manager"""
    return cache_manager.cached(ttl, key_prefix, key_builder, unless)


async def cache_get(key: str) -> Optional[Any]:
    """Shortcut to get from global cache"""
    return await cache_manager.get(key)


async def cache_set(key: str, value: Any, ttl: int = 3600) -> bool:
    """Shortcut to set in global cache"""
    return await cache_manager.set(key, value, ttl)


async def cache_delete(key: str) -> bool:
    """Shortcut to delete from global cache"""
    return await cache_manager.delete(key)


async def cache_clear_pattern(pattern: str) -> int:
    """Shortcut to clear pattern from global cache"""
    return await cache_manager.clear_pattern(pattern)
