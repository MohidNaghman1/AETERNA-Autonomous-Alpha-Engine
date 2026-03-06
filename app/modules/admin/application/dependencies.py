"""Admin role-based dependency injection.

Provides role validation dependencies for admin-only endpoints.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.config.db import SessionLocal
from app.modules.identity.infrastructure.models import UserRole
from app.shared.utils.auth_utils import decode_token
import logging

logger = logging.getLogger("admin-deps")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def extract_user_id_from_token(token: str) -> str:
    """Extract user_id from JWT token.

    Args:
        token: JWT token string

    Returns:
        str: User ID from token "sub" claim

    Raises:
        HTTPException: 401 if token invalid, expired, or missing user ID
    """
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )
        return str(user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


def require_role(role: str):
    """Create a dependency that requires a specific user role.

    Args:
        role: Required role name (e.g., 'admin')

    Returns:
        Depends: FastAPI dependency that checks the role

    Raises:
        HTTPException: 401 if token invalid/missing, 403 if role mismatch
    """

    def dependency(token: str = Depends(oauth2_scheme)):
        user_id = extract_user_id_from_token(token)
        db = SessionLocal()
        try:
            user_role = db.query(UserRole).filter(UserRole.user_id == int(user_id)).first()
            if not user_role or user_role.role != role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"{role.capitalize()} role required"
                )
            return True
        finally:
            db.close()

    return Depends(dependency)
