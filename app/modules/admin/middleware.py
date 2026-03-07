"""Admin authentication and authorization middleware.

Provides role-based access control (RBAC) checking for admin-only endpoints.
"""

from fastapi import HTTPException, status
from app.shared.utils.auth_utils import decode_token
import logging

logger = logging.getLogger("admin-middleware")


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
                detail="Invalid token: missing user ID",
            )
        return str(user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )


def get_admin_user_id(token: str = None) -> str:
    """Get and validate admin user from token.

    Args:
        token: JWT token (can be None for request-based extraction)

    Returns:
        str: Validated user ID
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    return extract_user_id_from_token(token)
