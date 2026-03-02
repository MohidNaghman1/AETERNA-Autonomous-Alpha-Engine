from fastapi import APIRouter, Depends
from app.modules.admin.middleware import admin_auth_required

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/metrics", dependencies=[Depends(admin_auth_required)])
def get_system_metrics():
    # Stub: Replace with real metrics aggregation
    return {
        "events_ingested_hourly": 120,
        "events_ingested_daily": 2400,
        "events_processed": 2300,
        "alerts_generated": 500,
        "active_users": 42,
        "system_uptime": "3 days, 4 hours",
        "error_rate": 0.01,
    }
