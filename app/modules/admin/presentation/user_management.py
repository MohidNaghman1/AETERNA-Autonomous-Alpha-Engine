from fastapi import APIRouter, HTTPException
from app.modules.admin.application.dependencies import require_role
from app.modules.identity.infrastructure.models import User
from app.config.db import SessionLocal

router = APIRouter(
    prefix="/admin/users",
    tags=["admin-users"],
    dependencies=[require_role("admin")],
)


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
