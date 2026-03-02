"""User identity and authentication services.

Provides core authentication functionality including user creation, token management,
password reset, and refresh token rotation.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.modules.identity.infrastructure.models import (
    User,
    RefreshToken,
    PasswordResetToken,
)
import secrets
from app.shared.utils.auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from datetime import datetime, timedelta
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "30")
)
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))


async def generate_password_reset_token(email: str, db: AsyncSession) -> tuple:
    """Generate a password reset token for a user.

    Args:
        email: User's email address
        db: Database session

    Returns:
        tuple: (token, expires_at) or (None, None) if user not found
    """
    user = await get_user_by_email(db, email)
    if not user:
        return None, None
    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)
    expires_at = datetime.utcnow() + timedelta(
        minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    )
    db_token = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        used=False,
    )
    db.add(db_token)
    await db.commit()
    return token, expires_at


def hash_token(token: str) -> str:
    """Hash a token using SHA256.

    Args:
        token: Token string to hash

    Returns:
        str: SHA256 hash of the token
    """
    return hashlib.sha256(token.encode()).hexdigest()


async def get_user_by_email(db: AsyncSession, email: str) -> User:
    """Retrieve a user by email address.

    Args:
        db: Database session
        email: User's email address

    Returns:
        User: User object or None if not found
    """
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, email: str, password: str) -> User:
    """Create a new user with email and password.

    Args:
        db: Database session
        email: User's email address
        password: Plaintext password (will be hashed)

    Returns:
        User: Created user object
    """
    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(email: str, password: str, db: AsyncSession) -> User:
    """Authenticate a user by email and password.

    Args:
        email: User's email address
        password: Plaintext password to verify
        db: Database session

    Returns:
        User: User object if authentication successful, None otherwise
    """
    user = await get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


async def issue_tokens(user, db: AsyncSession) -> tuple:
    """Issue access and refresh tokens for a user.

    Args:
        user: User object
        db: Database session

    Returns:
        tuple: (access_token, refresh_token)
    """
    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token({"sub": str(user.id), "email": user.email})
    token_hash = hash_token(refresh_token)
    db_refresh = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        revoked=False,
    )
    db.add(db_refresh)
    await db.commit()
    return access_token, refresh_token


async def rotate_refresh_token(refresh_token, db: AsyncSession) -> tuple:
    """Rotate a refresh token for a user.

    Revokes the old refresh token and issues a new one along with a new access token.

    Args:
        refresh_token: Current refresh token string
        db: Database session

    Returns:
        tuple: (new_access_token, new_refresh_token, user) or (None, None, None) if token invalid/expired
    """
    token_hash_val = hash_token(refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash_val, RefreshToken.revoked == False
        )
    )
    db_token = result.scalar_one_or_none()
    if not db_token or db_token.expires_at < datetime.utcnow():
        return None, None, None
    user = await db.get(User, db_token.user_id)
    db_token.revoked = True
    new_refresh_token = create_refresh_token({"sub": str(user.id), "email": user.email})
    new_db_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(new_refresh_token),
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        revoked=False,
    )
    db.add(new_db_token)
    await db.commit()
    new_access_token = create_access_token({"sub": str(user.id), "email": user.email})
    return new_access_token, new_refresh_token, user


async def revoke_refresh_token(refresh_token, db: AsyncSession) -> int:
    """Revoke a refresh token.

    Args:
        refresh_token: Refresh token string to revoke
        db: Database session

    Returns:
        int: 1 if revoked successfully, 0 if token not found
    """
    token_hash_val = hash_token(refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash_val)
    )
    db_token = result.scalar_one_or_none()
    if db_token:
        db_token.revoked = True
        await db.commit()
        return 1
    return 0


async def reset_password_with_token(
    token: str, new_password: str, db: AsyncSession
) -> tuple:
    """Reset user password using a password reset token.

    Args:
        token: Password reset token string
        new_password: New password to set (will be hashed)
        db: Database session

    Returns:
        tuple: (success: bool, message: str)
    """
    token_hash_val = hash_token(token)
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash_val,
            PasswordResetToken.used == False,
        )
    )
    db_token = result.scalar_one_or_none()
    if not db_token or db_token.expires_at < datetime.utcnow():
        return False, "Invalid or expired token"
    user = await db.get(User, db_token.user_id)
    if not user:
        return False, "User not found"
    user.password_hash = hash_password(new_password)
    db_token.used = True
    await db.commit()
    return True, "Password updated successfully"
