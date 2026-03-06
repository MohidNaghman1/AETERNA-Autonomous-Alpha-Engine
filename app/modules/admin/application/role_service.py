"""Admin role management service.

Provides business logic for role assignment and user permission management.
"""

from sqlalchemy.orm import Session
from app.modules.identity.infrastructure.models import UserRole, User
from fastapi import HTTPException, status
import logging

logger = logging.getLogger("role-service")


def assign_role(user_id: int, role: str, db: Session) -> dict:
    """Assign or update a user's role.

    Args:
        user_id: User ID to assign role to
        role: Role name (admin, viewer, etc.)
        db: Database session

    Returns:
        dict: Updated role information

    Raises:
        HTTPException: 404 if user not found, 400 for invalid operations
    """
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    # Check if role already exists
    existing_role = db.query(UserRole).filter(UserRole.user_id == user_id).first()
    
    if existing_role:
        # Update existing role
        logger.info(f"Updating user {user_id} role from {existing_role.role} to {role}")
        existing_role.role = role
    else:
        # Create new role
        logger.info(f"Assigning {role} role to user {user_id}")
        new_role = UserRole(user_id=user_id, role=role)
        db.add(new_role)
    
    db.commit()
    
    # Retrieve updated record
    updated_role = db.query(UserRole).filter(UserRole.user_id == user_id).first()
    return {
        "user_id": updated_role.user_id,
        "email": user.email,
        "role": updated_role.role,
        "message": f"✅ User assigned {role} role"
    }


def remove_role(user_id: int, db: Session) -> dict:
    """Remove a user's role (makes them viewer by default).

    Args:
        user_id: User ID to remove role from
        db: Database session

    Returns:
        dict: Confirmation message

    Raises:
        HTTPException: 404 if user/role not found
    """
    user_role = db.query(UserRole).filter(UserRole.user_id == user_id).first()
    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No role found for user {user_id}"
        )
    
    logger.info(f"Removing role from user {user_id}")
    db.delete(user_role)
    db.commit()
    
    return {
        "user_id": user_id,
        "message": "✅ Role removed, user is now viewer"
    }


def get_user_role(user_id: int, db: Session) -> dict:
    """Get a user's current role.

    Args:
        user_id: User ID to check
        db: Database session

    Returns:
        dict: User and role information

    Raises:
        HTTPException: 404 if user not found
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    user_role = db.query(UserRole).filter(UserRole.user_id == user_id).first()
    
    return {
        "user_id": user_id,
        "email": user.email,
        "role": user_role.role if user_role else "viewer",
        "has_admin": user_role and user_role.role == "admin"
    }


def list_all_roles(db: Session) -> list:
    """List all user roles in system.

    Args:
        db: Database session

    Returns:
        list: All role assignments with user emails
    """
    roles = db.query(UserRole).all()
    result = []
    
    for role in roles:
        user = db.query(User).filter(User.id == role.user_id).first()
        result.append({
            "user_id": role.user_id,
            "email": user.email if user else "unknown",
            "role": role.role
        })
    
    return result


def list_admins(db: Session) -> list:
    """List all admin users.

    Args:
        db: Database session

    Returns:
        list: All users with admin role
    """
    admin_roles = db.query(UserRole).filter(UserRole.role == "admin").all()
    result = []
    
    for role in admin_roles:
        user = db.query(User).filter(User.id == role.user_id).first()
        result.append({
            "user_id": role.user_id,
            "email": user.email if user else "unknown",
            "role": "admin"
        })
    
    return result
