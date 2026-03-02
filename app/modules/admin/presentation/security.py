"""Security middleware and utilities.

Provides rate limiting and input sanitization for API endpoints.
"""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import re


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for basic in-memory rate limiting.

    Tracks requests per IP address in 60-second windows and rejects requests
    exceeding the configured limit.

    Attributes:
        RATE_LIMIT: Maximum number of requests allowed per minute per IP
        requests: Dict tracking request counts keyed by IP:window
    """

    RATE_LIMIT = 100
    requests = {}

    async def dispatch(self, request: Request, call_next):
        """Process request and apply rate limiting.

        Args:
            request: HTTP request
            call_next: Next middleware handler

        Returns:
            Response from next handler

        Raises:
            HTTPException: 429 if rate limit exceeded
        """
        ip = request.client.host
        from time import time

        now = int(time())
        window = now // 60
        key = f"{ip}:{window}"
        self.requests[key] = self.requests.get(key, 0) + 1
        if self.requests[key] > self.RATE_LIMIT:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        return await call_next(request)


def sanitize_input(data: str) -> str:
    """Remove potentially dangerous characters from input string.

    Sanitizes against basic injection patterns by removing special characters.
    For production, use parameterized queries and proper ORM layers (currently implemented).

    Args:
        data: Input string to sanitize

    Returns:
        str: Sanitized string with dangerous characters removed, or original value if not a string
    """
    if isinstance(data, str):
        return re.sub(r'[<>"\'%;()]', "", data)
    return data
