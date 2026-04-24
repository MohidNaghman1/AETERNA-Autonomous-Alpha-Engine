"""Pydantic schemas for authentication and user identity API endpoints.

Defines request/response models for user registration, login, password reset,
and profile management.
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, Dict, Any


class RegisterRequest(BaseModel):
    """Request to register a new user account.

    Attributes:
        email: User email address
        password: Password (minimum 8 characters)
    """

    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    """Request to login and get access token.

    Attributes:
        email: User email address
        password: User password
    """

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Request to refresh access token.

    Attributes:
        refresh_token: Valid refresh token from previous login
    """

    refresh_token: str


class TokenResponse(BaseModel):
    """Response containing authentication tokens.

    Attributes:
        access_token: JWT access token for authenticated requests
        refresh_token: JWT refresh token for token rotation
        token_type: Token type (always "bearer")
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class PasswordResetRequest(BaseModel):
    """Request to initiate password reset.

    Attributes:
        email: Email address of account to reset
    """

    email: EmailStr


class PasswordResetTokenResponse(BaseModel):
    """Response confirming password reset email was sent.

    Security note: Reset token is sent only via email, not in response.

    Attributes:
        message: Confirmation message
        email: Email address where reset link was sent
    """

    message: str
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    """Request to confirm password reset with token.

    Attributes:
        token: Password reset token from email
        new_password: New password (minimum 8 characters)
    """

    token: str
    new_password: str = Field(min_length=8)


class PasswordResetConfirmResponse(BaseModel):
    """Response from password reset confirmation.

    Attributes:
        success: Whether password reset was successful
        message: Status message
    """

    success: bool
    message: str


class UserProfileResponse(BaseModel):
    """User profile information response.

    Attributes:
        id: User ID
        email: User email address
        telegram_id: Optional Telegram chat ID for alerts
        preferences: Optional dict of user preferences
        created_at: Account creation timestamp
        email_verified: Whether email has been verified
    """

    id: int
    email: EmailStr
    telegram_id: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    created_at: datetime
    email_verified: bool


class UserProfileUpdateRequest(BaseModel):
    telegram_id: str = None
    preferences: dict = None
