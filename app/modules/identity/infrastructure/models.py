"""SQLAlchemy models for user identity and authentication.

Defines database schemas for users, preferences, refresh tokens, roles, and password resets.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, ForeignKey, Index
from datetime import datetime
from app.config.db import Base


class User(Base):
    """User account model.

    Stores user credentials and account information.

    Attributes:
        id: Primary key
        email: Unique email address
        password_hash: Bcrypt password hash
        telegram_id: Optional unique Telegram chat ID
        preferences: JSON user preferences
        created_at: Account creation timestamp
        email_verified: Email verification status
    """

    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    telegram_id = Column(String, unique=True, nullable=True)
    preferences = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    email_verified = Column(Boolean, default=False)


class UserPreference(Base):
    """User preferences model.

    Stores user-specific alert and delivery preferences.

    Attributes:
        id: Primary key
        user_id: Unique foreign key to users table
        preferences: JSON preferences dict (watchlist, frequency, quiet_hours)
    """

    __tablename__ = "user_preferences"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, unique=True)
    preferences = Column(JSON, nullable=True)


class RefreshToken(Base):
    """Refresh token model for JWT rotation.

    Stores refresh tokens used to obtain new access tokens.

    Attributes:
        id: Primary key
        user_id: Foreign key to users table
        token_hash: SHA256 hash of the refresh token
        expires_at: Token expiration timestamp
        revoked: Whether token has been revoked
    """

    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)


class UserRole(Base):
    """User role model for role-based access control (RBAC).

    Assigns roles to users for permission management.

    Attributes:
        id: Primary key
        user_id: Unique foreign key to users table
        role: Role name (admin, viewer, etc.)
    """

    __tablename__ = "user_roles"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    role = Column(String, nullable=False, default="viewer")


Index("ix_user_roles_role", UserRole.role)


class PasswordResetToken(Base):
    """Password reset token model.

    Stores one-time tokens for password reset functionality.

    Attributes:
        id: Primary key
        user_id: Foreign key to users table
        token_hash: SHA256 hash of the reset token
        expires_at: Token expiration timestamp
        used: Whether token has been used
    """

    __tablename__ = "password_reset_tokens"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
