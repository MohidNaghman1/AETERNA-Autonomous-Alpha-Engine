from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON,ForeignKey
from datetime import datetime
from app.config.db import Base
from sqlalchemy import Index



class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True,autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    telegram_id = Column(String, unique=True, nullable=True)
    preferences = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    email_verified = Column(Boolean, default=False)


class UserPreference(Base):
    __tablename__ = "user_preferences"
    id = Column(Integer, primary_key=True, index=True,autoincrement=True)
    user_id = Column(Integer, nullable=False, unique=True)
    preferences = Column(JSON, nullable=True)  # watchlist, frequency, quiet_hours

# --- RefreshToken Model for Auth ---

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, index=True,autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)



# --- UserRole Model for RBAC ---

class UserRole(Base):
    __tablename__ = "user_roles"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    role = Column(String, nullable=False, default="viewer")  # e.g., admin, viewer

# Add index for role
Index('ix_user_roles_role', UserRole.role)

# --- PasswordResetToken Model for Password Reset ---
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id = Column(Integer, primary_key=True, index=True,autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)