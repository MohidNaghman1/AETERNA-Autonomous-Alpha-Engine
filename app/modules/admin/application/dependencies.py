from fastapi import Depends, HTTPException, Request
from app.config.db import AsyncSessionLocal as SessionLocal
from app.modules.identity.infrastructure.models import UserRole

def require_role(role: str):
    def dependency(request: Request):
        user_id = request.headers.get("X-User-Id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID required")
        db = SessionLocal()
        user_role = db.query(UserRole).filter(UserRole.user_id == int(user_id)).first()
        db.close()
        if not user_role or user_role.role != role:
            raise HTTPException(status_code=403, detail=f"{role.capitalize()} role required")
        return True
    return Depends(dependency)
