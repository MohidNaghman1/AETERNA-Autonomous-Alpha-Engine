"""Admin authentication and authorization middleware.

Provides role-based access control (RBAC) checking for admin-only endpoints.
"""

from fastapi import Request, HTTPException
from functools import wraps
from app.config.db import AsyncSessionLocal as SessionLocal
from app.modules.identity.infrastructure.models import UserRole
def admin_auth_required(request: Request) -> bool:
    """Check if request user has admin role.
    
    Args:
        request: FastAPI request object
        
    Returns:
        bool: True if user is admin
        
    Raises:
        HTTPException: 401 if user_id missing, 403 if not admin
    """
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID required")
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
