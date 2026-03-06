"""Admin authentication and authorization middleware.

Provides role-based access control (RBAC) checking for admin-only endpoints.
"""

from fastapi import Request, HTTPException
from functools import wraps
from app.config.db import AsyncSessionLocal as SessionLocal
from app.modules.identity.infrastructure.models import UserRole
from app.shared.utils.auth_utils import decode_token
import logging

logger = logging.getLogger("admin-middleware")


def extract_user_id_from_token(request: Request) -> str:
    """Extract user_id from JWT token in Authorization header.

    Args:
        request: FastAPI request object

    Returns:
        str: User ID from token "sub" claim

    Raises:
        HTTPException: 401 if token missing, invalid, or expired
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    try:
        scheme, token = auth_header.split(" ")
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
        return str(user_id)
    except Exception as e:
        logger.error(f"Token decode error: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def admin_auth_required(request: Request) -> bool:
    """Check if request user has admin role.

    Args:
        request: FastAPI request object

    Returns:
        bool: True if user is admin

    Raises:
        HTTPException: 401 if token invalid/missing, 403 if not admin
    """
    user_id = extract_user_id_from_token(request)
    db = SessionLocal()
    user_role = db.query(UserRole).filter(UserRole.user_id == int(user_id)).first()
    db.close()
    if not user_role or user_role.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return True


def admin_only(func):
    """Decorator for admin-only function-based endpoints.

    Args:
        func: Endpoint function to protect

    Returns:
        Wrapped function that enforces admin authentication

    Raises:
        HTTPException: 403 if user is not admin
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        request = kwargs.get("request")
        if not request or not admin_auth_required(request):
            raise HTTPException(status_code=403, detail="Admin access required")
        return func(*args, **kwargs)

    return wrapper
