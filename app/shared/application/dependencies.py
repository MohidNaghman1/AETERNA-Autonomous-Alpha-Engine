"""Dependency injection for FastAPI endpoints.

Provides database session management and JWT token-based user authentication.
Includes OAuth2 security setup and current user extraction.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.shared.utils.auth_utils import decode_token
from app.modules.identity.infrastructure.models import User
from app.config.db import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import logging

logger = logging.getLogger("auth-deps")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Database session dependency
async def get_db() -> AsyncSession:
    """Get an async database session.
    
    Provides a SQLAlchemy AsyncSession for use in endpoints.
    Session is automatically closed after use.
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate current authenticated user from JWT token.
    
    Decodes JWT token, validates format, retrieves user from database.
    Must be used as a dependency in protected endpoints.
    
    Args:
        token: JWT bearer token from Authorization header
        db: Database session
        
    Returns:
        User: Authenticated user object
        
    Raises:
        HTTPException: 401 if token invalid, expired, or user not found
        HTTPException: 500 if unexpected error during authentication
    """
    try:
        payload = decode_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
            )
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting current user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to extract current user")
