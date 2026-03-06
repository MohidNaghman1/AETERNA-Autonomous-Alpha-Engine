"""Bootstrap admin creation - only works once during initial setup."""

from fastapi import APIRouter, HTTPException, status
from app.config.db import AsyncSessionLocal as SessionLocal
from app.modules.identity.infrastructure.models import UserRole, User
from pydantic import BaseModel
import os
import logging

logger = logging.getLogger("bootstrap")

router = APIRouter(
    prefix="/api/bootstrap",
    tags=["bootstrap"],
)


class CreateFirstAdminRequest(BaseModel):
    """Request to create first admin.
    
    Attributes:
        user_id: User ID to make admin
        bootstrap_token: Secret token from BOOTSTRAP_TOKEN env var
    """
    user_id: int
    bootstrap_token: str


@router.post("/create-first-admin")
def create_first_admin(data: CreateFirstAdminRequest):
    """Create the first admin user during setup.
    
    **BOOTSTRAP ONLY** - Only works if no admin exists yet!
    
    Requires BOOTSTRAP_TOKEN environment variable.
    
    Args:
        data: User ID and bootstrap token
        
    Returns:
        dict: Admin creation confirmation
        
    Raises:
        403: If admins already exist or token invalid
        404: If user not found
    """
    # Check if bootstrap token is valid
    valid_token = os.getenv("BOOTSTRAP_TOKEN", "")
    if not valid_token or data.bootstrap_token != valid_token:
        logger.warning(f"Invalid bootstrap token attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid bootstrap token"
        )
    
    db = SessionLocal()
    try:
        # Check if any admin already exists
        existing_admin = db.query(UserRole).filter(
            UserRole.role == "admin"
        ).first()
        
        if existing_admin:
            logger.warning(f"Bootstrap attempt when admin exists: user {existing_admin.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="❌ Admin already exists! Bootstrap disabled for security."
            )
        
        # Verify user exists
        user = db.query(User).filter(User.id == data.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {data.user_id} not found"
            )
        
        # Check if user already has a role
        existing_role = db.query(UserRole).filter(
            UserRole.user_id == data.user_id
        ).first()
        
        if existing_role:
            # Update existing role to admin
            logger.info(f"Bootstrap: Updating user {data.user_id} to admin")
            existing_role.role = "admin"
        else:
            # Create new admin role
            logger.info(f"Bootstrap: Creating admin role for user {data.user_id}")
            admin_role = UserRole(user_id=data.user_id, role="admin")
            db.add(admin_role)
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"✅ User {data.user_id} ({user.email}) is now ADMIN",
            "user_id": data.user_id,
            "email": user.email,
            "role": "admin",
            "warning": "⚠️ This endpoint is now DISABLED (bootstrap disabled)"
        }
        
    finally:
        db.close()
