
from fastapi import Request, HTTPException
from functools import wraps
from app.config.db import AsyncSessionLocal as SessionLocal
from app.modules.identity.infrastructure.models import UserRole

# RBAC: check user role from DB
def admin_auth_required(request: Request):
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    db = SessionLocal()
    user_role = db.query(UserRole).filter(UserRole.user_id == int(user_id)).first()
    db.close()
    if not user_role or user_role.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return True

# Decorator for admin-only routes (for function-based endpoints)
def admin_only(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        request = kwargs.get("request")
        if not request or not admin_auth_required(request):
            raise HTTPException(status_code=403, detail="Admin access required")
        return func(*args, **kwargs)
    return wrapper
