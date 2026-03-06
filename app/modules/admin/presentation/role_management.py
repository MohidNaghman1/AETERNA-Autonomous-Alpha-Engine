"""Admin role management endpoints.

Provides APIs for assigning and managing user roles (RBAC).
Only accessible to admin users.
"""

from fastapi import APIRouter, HTTPException, status
from app.modules.admin.application.dependencies import require_role
from app.modules.admin.application.role_service import (
    assign_role,
    remove_role,
    get_user_role,
    list_all_roles,
    list_admins,
)
from app.config.db import SessionLocal
from pydantic import BaseModel

router = APIRouter(
    prefix="/api/admin/roles",
    tags=["admin-roles"],
    dependencies=[require_role("admin")],
)


class AssignRoleRequest(BaseModel):
    """Request to assign role to user.
    
    Attributes:
        role: Role name (admin, viewer, editor, etc.)
    """
    role: str


@router.get("/")
def list_roles():
    """List all user roles in system.
    
    **Admin only endpoint**
    
    Returns:
        list: All role assignments
    """
    db = SessionLocal()
    try:
        roles = list_all_roles(db)
        return {
            "total": len(roles),
            "roles": roles
        }
    finally:
        db.close()


@router.get("/admins")
def get_admins():
    """List all admin users.
    
    **Admin only endpoint**
    
    Returns:
        list: All users with admin role
    """
    db = SessionLocal()
    try:
        admins = list_admins(db)
        return {
            "total": len(admins),
            "admins": admins
        }
    finally:
        db.close()


@router.get("/{user_id}")
def get_role(user_id: int):
    """Get a user's current role.
    
    **Admin only endpoint**
    
    Args:
        user_id: User ID to check
        
    Returns:
        dict: User role information
    """
    db = SessionLocal()
    try:
        role_info = get_user_role(user_id, db)
        return role_info
    finally:
        db.close()


@router.post("/{user_id}/assign")
def assign_user_role(user_id: int, data: AssignRoleRequest):
    """Assign or update a user's role.
    
    **Admin only endpoint**
    
    Args:
        user_id: User ID to assign role to
        data: AssignRoleRequest with role name
        
    Returns:
        dict: Updated role information
        
    Raises:
        404: User not found
        403: Unauthorized
    """
    if not data.role or data.role.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role name cannot be empty"
        )
    
    db = SessionLocal()
    try:
        result = assign_role(user_id, data.role.lower(), db)
        return result
    finally:
        db.close()


@router.delete("/{user_id}/remove")
def remove_user_role(user_id: int):
    """Remove a user's role (revert to viewer).
    
    **Admin only endpoint**
    
    Args:
        user_id: User ID to remove role from
        
    Returns:
        dict: Confirmation message
        
    Raises:
        404: User or role not found
        403: Unauthorized
    """
    db = SessionLocal()
    try:
        result = remove_role(user_id, db)
        return result
    finally:
        db.close()
