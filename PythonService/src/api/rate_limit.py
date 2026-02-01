"""
Rate Limiting Middleware
Protects API endpoints from abuse using rate limiting
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException
from typing import Callable


def create_limiter():
    """Create and configure rate limiter"""

    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["200/minute"],  # 200 requests per minute by default
        storage_uri="memory://",  # Use in-memory storage
        enabled=True  # Can be disabled via config
    )

    return limiter


# Global limiter instance
limiter = create_limiter()


def get_rate_limit_config(endpoint: str) -> tuple:
    """
    Get rate limit configuration for specific endpoint

    Returns (limit, period) tuple
    """
    configs = {
        # Transcription endpoints (more restrictive due to heavy processing)
        "transcribe": ("10/minute",),
        "upload": ("10/minute",),
        "upload-long": ("5/minute",),
        "batch-transcribe": ("3/minute",),

        # Model configuration (less restrictive)
        "config": ("60/minute",),
        "models": ("60/minute",),

        # Post-processing (moderate)
        "text": ("30/minute",),

        # Session management (moderate)
        "start": ("20/minute",),
        "stop": ("20/minute",),

        # Health checks (very permissive)
        "health": ("1000/minute",),
        "status": ("100/minute",),

        # WebSocket (no rate limiting on the connection itself)
        "stream": None,
        "stream-progress": None,
    }

    return configs.get(endpoint, ("200/minute",))


def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded"""

    import json

    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "message": f"Too many requests. Limit: {exc.detail}",
            "retry_after": getattr(exc, "retry_after", 60)
        },
        headers={
            "Retry-After": str(getattr(exc, "retry_after", 60))
        }
    )


from fastapi.responses import JSONResponse


def check_rate_limit(endpoint: str):
    """
    Decorator to check rate limit for specific endpoint

    Usage:
        @check_rate_limit("transcribe")
        async def my_endpoint(...):
            ...
    """

    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # Get rate limit config for endpoint
            config = get_rate_limit_config(endpoint)

            if config is None:
                # No rate limiting for this endpoint
                return await func(*args, **kwargs)

            # Apply rate limit
            limit = config[0]
            return limiter.limit(limit)(func)(*args, **kwargs)

        return wrapper

    return decorator
