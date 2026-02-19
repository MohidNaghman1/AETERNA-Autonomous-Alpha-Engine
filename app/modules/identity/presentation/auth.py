from fastapi import APIRouter, HTTPException, Depends, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.db import AsyncSessionLocal
from app.modules.identity.application import services
from app.modules.identity.presentation.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, PasswordResetRequest, PasswordResetTokenResponse,
    PasswordResetConfirmRequest, PasswordResetConfirmResponse, UserProfileResponse, UserProfileUpdateRequest, RefreshRequest
)
from app.shared.application.dependencies import get_db, get_current_user

router = APIRouter()



@router.post("/register", response_model=TokenResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await services.get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = await services.create_user(db, data.email, data.password)
    access_token, refresh_token = await services.issue_tokens(user, db)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await services.authenticate_user(data.email, data.password, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token, refresh_token = await services.issue_tokens(user, db)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)



@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    new_access_token, new_refresh_token, user = await services.rotate_refresh_token(data.refresh_token, db)
    if not new_access_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return TokenResponse(access_token=new_access_token, refresh_token=new_refresh_token)

@router.post("/password-reset/request", response_model=PasswordResetTokenResponse)
async def password_reset_request(data: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    token, expires_at = await services.generate_password_reset_token(data.email, db)
    if not token:
        raise HTTPException(status_code=404, detail="User not found")
    # In production, send token via email instead of returning it!
    return PasswordResetTokenResponse(reset_token=token, expires_at=expires_at)

@router.post("/password-reset/confirm", response_model=PasswordResetConfirmResponse)
async def password_reset_confirm(data: PasswordResetConfirmRequest, db: AsyncSession = Depends(get_db)):
    success, message = await services.reset_password_with_token(data.token, data.new_password, db)
    return PasswordResetConfirmResponse(success=success, message=message)


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(current_user=Depends(get_current_user)):
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        telegram_id=current_user.telegram_id,
        preferences=current_user.preferences,
        created_at=current_user.created_at,
        email_verified=current_user.email_verified,
    )

@router.patch("/profile", response_model=UserProfileResponse)
async def update_profile(
    data: UserProfileUpdateRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if data.telegram_id is not None:
        current_user.telegram_id = data.telegram_id
    if data.preferences is not None:
        current_user.preferences = data.preferences
    await db.commit()
    await db.refresh(current_user)
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        telegram_id=current_user.telegram_id,
        preferences=current_user.preferences,
        created_at=current_user.created_at,
        email_verified=current_user.email_verified,
    )
