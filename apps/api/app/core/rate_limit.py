"""Rate limiting implementation"""

import time
from typing import Optional, Callable
from functools import wraps
from fastapi import Request, HTTPException, status

from app.core.cache import cache_manager
from app.core.exceptions import RateLimitError


class RateLimiter:
    """Rate limiter using sliding window algorithm"""

    def __init__(
        self,
        requests: int = 100,
        window: int = 60,  # seconds
        key_prefix: str = "ratelimit"
    ):
        self.requests = requests
        self.window = window
        self.key_prefix = key_prefix

    def _get_key(self, identifier: str) -> str:
        """Generate rate limit key"""
        return f"{self.key_prefix}:{identifier}"

    async def is_allowed(self, identifier: str) -> tuple[bool, dict]:
        """Check if request is allowed"""
        key = self._get_key(identifier)
        now = int(time.time())
        window_start = now - self.window

        # Get current window data
        data = await cache_manager.get(key) or {"requests": [], "count": 0}

        # Filter out old requests outside the window
        valid_requests = [ts for ts in data.get("requests", []) if ts > window_start]

        # Check if allowed
        if len(valid_requests) >= self.requests:
            # Rate limit exceeded
            retry_after = valid_requests[0] + self.window - now
            return False, {
                "limit": self.requests,
                "remaining": 0,
                "reset": valid_requests[0] + self.window,
                "retry_after": max(0, retry_after)
            }

        # Update requests
        valid_requests.append(now)
        await cache_manager.set(key, {"requests": valid_requests}, ttl=self.window)

        return True, {
            "limit": self.requests,
            "remaining": self.requests - len(valid_requests) - 1,
            "reset": now + self.window
        }

    async def check(self, identifier: str):
        """Check rate limit and raise exception if exceeded"""
        allowed, info = await self.is_allowed(identifier)

        if not allowed:
            raise RateLimitError(
                message=f"Rate limit exceeded. Try again in {info['retry_after']} seconds.",
                retry_after=info["retry_after"]
            )

        return info


def rate_limit(
    requests: int = 100,
    window: int = 60,
    key_func: Optional[Callable] = None
):
    """Decorator for rate limiting endpoints"""
    limiter = RateLimiter(requests, window)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request in args/kwargs
            request = None
            for arg in args + tuple(kwargs.values()):
                if isinstance(arg, Request):
                    request = arg
                    break

            if request:
                # Get identifier
                if key_func:
                    identifier = key_func(request)
                else:
                    identifier = _default_key_func(request)

                # Check rate limit
                info = await limiter.check(identifier)

                # Store info for response headers
                request.state.rate_limit_info = info

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def _default_key_func(request: Request) -> str:
    """Default function to extract identifier from request"""
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"

    client = request.client
    if client:
        return f"ip:{client.host}"

    return "ip:unknown"


def get_rate_limiter(endpoint_type: str = "default"):
    """Get rate limiter for endpoint type"""
    configs = {
        "default": {"requests": 100, "window": 60},
        "auth": {"requests": 5, "window": 60},
        "sensitive": {"requests": 10, "window": 60},
        "ai_generation": {"requests": 10, "window": 60},
        "export": {"requests": 5, "window": 60},
    }
    config = configs.get(endpoint_type, configs["default"])
    return RateLimiter(**config)
