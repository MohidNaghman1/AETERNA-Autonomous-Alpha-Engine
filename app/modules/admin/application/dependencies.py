"""Admin role-based dependency injection.

Provides role validation dependencies for admin-only endpoints.
"""

from fastapi import Depends, HTTPException, Request
from app.config.db import AsyncSessionLocal as SessionLocal
from app.modules.identity.infrastructure.models import UserRole


def require_role(role: str):
    """Create a dependency that requires a specific user role.

    Args:
        role: Required role name (e.g., 'admin')

    Returns:
        Depends: FastAPI dependency that checks the role

    Raises:
        HTTPException: 401 if user_id missing, 403 if role mismatch
    """

    def dependency(request: Request):
        user_id = request.headers.get("X-User-Id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID required")
        db = SessionLocal()
        user_role = db.query(UserRole).filter(UserRole.user_id == int(user_id)).first()
        db.close()
        if not user_role or user_role.role != role:
            raise HTTPException(
                status_code=403, detail=f"{role.capitalize()} role required"
            )
        return True

    return Depends(dependency)
