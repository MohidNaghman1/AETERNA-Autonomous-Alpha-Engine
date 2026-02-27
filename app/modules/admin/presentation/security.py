from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import re

class RateLimitMiddleware(BaseHTTPMiddleware):
    # Simple in-memory rate limiting (demo)
    RATE_LIMIT = 100  # requests per minute
    requests = {}

    async def dispatch(self, request, call_next):
        ip = request.client.host
        from time import time
        now = int(time())
        window = now // 60
        key = f"{ip}:{window}"
        self.requests[key] = self.requests.get(key, 0) + 1
        if self.requests[key] > self.RATE_LIMIT:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        return await call_next(request)

# Input sanitization and SQL injection prevention
# Use parameterized queries (SQLAlchemy ORM)
# XSS prevention: escape output in templates, validate input

def sanitize_input(data):
    # Remove dangerous characters (demo)
    if isinstance(data, str):
        return re.sub(r'[<>"\'%;()]', '', data)
    return data
