from fastapi import APIRouter, Request
from app.modules.admin.application.dependencies import require_role
from app.modules.admin.presentation.security import sanitize_input

router = APIRouter(prefix="admin/protected", tags=["admin-protected"])


@router.get("/secret", dependencies=[require_role("admin")])
def admin_secret(request: Request):
    msg = request.query_params.get("msg", "This is an admin-only endpoint!")
    return {"message": sanitize_input(msg)}
