from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from app.modules.admin.application.dependencies import require_role
from app.modules.identity.infrastructure.models import User
from app.config.db import SessionLocal
from app.shared.utils.auth_utils import hash_password
from sqlalchemy.exc import IntegrityError

router = APIRouter(
    prefix="/api/admin/users",
    tags=["admin-users"],
    dependencies=[require_role("admin")],
)


class CreateUserRequest(BaseModel):
    """Request model for creating a new user."""
    id: int
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Response model for user data."""
    id: int
    email: str
    created_at: str


@router.post("/", response_model=UserResponse)
def create_user(request: CreateUserRequest):
    """Create a new user with specified id, email, and password.
    
    Args:
        request: CreateUserRequest with id, email, password
        
    Returns:
        Created user details
        
    Raises:
        HTTPException: If user with id already exists or email is invalid
    """
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.id == request.id) | (User.email == request.email)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=409, 
                detail=f"User with id {request.id} or email {request.email} already exists"
            )
        
        # Hash the password
        hashed_password = hash_password(request.password)
        
        # Create new user
        new_user = User(
            id=request.id,
            email=request.email,
            password_hash=hashed_password,
            email_verified=False
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return UserResponse(
            id=new_user.id,
            email=new_user.email,
            created_at=new_user.created_at.isoformat() if new_user.created_at else None
        )
        
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Failed to create user - constraint violation"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.get("/")
def list_users():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        return [
            {
                "id": u.id,
                "email": u.email,
                "active": u.email_verified,
                "created_at": u.created_at,
            }
            for u in users
        ]
    finally:
        db.close()


@router.get("/{user_id}")
def view_user_details(user_id: int):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "id": user.id,
            "email": user.email,
            "active": user.email_verified,
            "created_at": user.created_at,
            "telegram_id": user.telegram_id,
            "preferences": user.preferences,
        }
    finally:
        db.close()


@router.patch("/{user_id}/toggle")
def toggle_user_status(user_id: int):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.email_verified = not user.email_verified
        db.commit()
        db.refresh(user)
        return {"id": user.id, "active": user.email_verified}
    finally:
        db.close()
