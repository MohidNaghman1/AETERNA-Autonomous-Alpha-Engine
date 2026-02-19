
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, Dict, Any

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetTokenResponse(BaseModel):
    reset_token: str
    expires_at: datetime

class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)

class PasswordResetConfirmResponse(BaseModel):
    success: bool
    message: str

class UserProfileResponse(BaseModel):
    id: int
    email: EmailStr
    telegram_id: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    created_at: datetime
    email_verified: bool

class UserProfileUpdateRequest(BaseModel):
    telegram_id: str = None
    preferences: dict = None

class RefreshRequest(BaseModel):
    refresh_token: str
