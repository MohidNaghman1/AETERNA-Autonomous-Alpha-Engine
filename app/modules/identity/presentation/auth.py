from fastapi.responses import HTMLResponse
from app.modules.identity.application.services import get_user_by_email
from fastapi import APIRouter, HTTPException, Depends, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.db import AsyncSessionLocal
from app.modules.identity.application import services
from app.modules.identity.presentation.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    PasswordResetRequest,
    PasswordResetTokenResponse,
    PasswordResetConfirmRequest,
    PasswordResetConfirmResponse,
    UserProfileResponse,
    UserProfileUpdateRequest,
    RefreshRequest,
)
from app.shared.utils.email_utils import send_password_reset_email
from app.shared.application.dependencies import get_db, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await services.get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = await services.create_user(db, data.email, data.password)
    access_token, refresh_token = await services.issue_tokens(user, db)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 compatible token endpoint.
    Accepts form data (username/password) from Swagger UI or form submissions.
    Username should be the email address.
    """
    user = await services.authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token, refresh_token = await services.issue_tokens(user, db)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    new_access_token, new_refresh_token, user = await services.rotate_refresh_token(
        data.refresh_token, db
    )
    if not new_access_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return TokenResponse(access_token=new_access_token, refresh_token=new_refresh_token)


@router.post("/password-reset/request", response_model=PasswordResetTokenResponse)
async def password_reset_request(data: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    """
    Request a password reset.

    P0 Security Fix: Response no longer contains the reset token!
    The token is sent ONLY via email for security.
    This prevents token interception via:
    - HTTP request logs
    - Browser history
    - Network proxies

    Endpoint returns a generic success message to avoid user enumeration.
    """
    token, expires_at = await services.generate_password_reset_token(data.email, db)

    # Send token via email (NOT in response)
    if token:
        try:
            await send_password_reset_email(data.email, token)
            print(f"[AUTH] Password reset email sent to {data.email}")
        except Exception as e:
            print(f"[AUTH-ERROR] Failed to send password reset email to {data.email}: {e}")
            # Continue even if email fails - user can try again

    # Return generic response (doesn't reveal if email exists)
    return PasswordResetTokenResponse(
        message="If an account with this email exists, a password reset link has been sent. Check your email.",
        email=data.email,
    )


@router.post("/password-reset/confirm", response_model=PasswordResetConfirmResponse)
async def password_reset_confirm(
    data: PasswordResetConfirmRequest, db: AsyncSession = Depends(get_db)
):
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


# Unsubscribe endpoint (public, by email)
@router.get("/unsubscribe", response_class=HTMLResponse)
async def unsubscribe(email: str, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, email)
    if not user:
        return HTMLResponse("<h3>User not found.</h3>", status_code=404)
    prefs = user.preferences or {}
    prefs["unsubscribe"] = True
    user.preferences = prefs
    await db.commit()
    return HTMLResponse("<h3>You have been unsubscribed from all emails.</h3>")
