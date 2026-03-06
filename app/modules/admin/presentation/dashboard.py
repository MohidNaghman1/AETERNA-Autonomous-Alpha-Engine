from fastapi import APIRouter
from app.modules.admin.application.dependencies import require_role

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/metrics", dependencies=[require_role("admin")])
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
